import logging
import os
import tempfile
from datetime import UTC, datetime
from urllib.parse import urlparse

import requests
from flask import current_app

from udata.core import storages
from udata.core.dataset.models import Dataset, Resource
from udata.core.storages.utils import md5
from udata.tasks import job, task

from .client import GeopfClient, GeopfError, GeopfTimeoutError
from .metadata import dataset_to_iso19115

log = logging.getLogger(__name__)


@task(name="geopf.push_resource", bind=True, ignore_result=False)
def push_resource_to_geopf(self, dataset_id, resource_id):
    log.info("geopf: starting push dataset=%s resource=%s", dataset_id, resource_id)
    dataset = Dataset.objects.get(id=dataset_id)
    resource = next((r for r in dataset.resources if str(r.id) == resource_id), None)
    if resource is None:
        log.error("geopf: resource not found dataset=%s resource=%s", dataset_id, resource_id)
        return

    if not resource.format or resource.format.lower() != "gpkg":
        return

    datastore_id = current_app.config.get("GEOPF_DATASTORE_ID")
    if not datastore_id or not current_app.config.get("GEOPF_TOKEN"):
        log.warning(
            "geopf: GEOPF_TOKEN or GEOPF_DATASTORE_ID not configured, skipping push dataset=%s resource=%s",
            dataset_id,
            resource_id,
        )
        return

    _set_extras(
        dataset, resource, {"geopf:push:status": "pending", "geopf:push:task-id": self.request.id}
    )

    try:
        _run_pipeline(dataset, resource, datastore_id)
    except GeopfTimeoutError as e:
        log.exception("geopf: pipeline timed out dataset=%s resource=%s", dataset_id, resource_id)
        _set_extras(dataset, resource, {"geopf:push:status": "timeout", "geopf:push:error": str(e)})
        raise
    except Exception as e:
        log.exception("geopf: pipeline failed dataset=%s resource=%s", dataset_id, resource_id)
        _set_extras(dataset, resource, {"geopf:push:status": "error", "geopf:push:error": str(e)})
        raise


def _run_pipeline(dataset, resource, datastore_id):
    client = GeopfClient()
    datasheet_name = str(dataset.id)
    stored_data_name = f"_{resource.id}"
    filename = _resource_filename(resource)
    dataset_id = dataset.id
    resource_id = resource.id

    upload_id = None
    stored_data_id = None

    try:
        with _open_resource_file(resource) as f:
            file_md5 = md5(f, seek_zero=True)

            upload_id = client.create_upload(
                name=stored_data_name,
                description=dataset.title,
            )
            log.info(
                "geopf: created upload=%s dataset=%s resource=%s",
                upload_id,
                dataset_id,
                resource_id,
            )

            client.push_file(upload_id, f, filename)
            client.push_md5(upload_id, filename, file_md5)
            client.close_upload(upload_id)

        log.info(
            "geopf: waiting for upload checks upload=%s dataset=%s resource=%s",
            upload_id,
            dataset_id,
            resource_id,
        )
        status = client.poll_upload(upload_id)
        if status != "CLOSED":
            raise GeopfError(f"Upload checks failed with status {status}")

        client.tag_entity("uploads", upload_id, datasheet_name)

        exec_id = client.launch_processing(upload_id, stored_data_name)
        log.info(
            "geopf: launched processing execution=%s dataset=%s resource=%s",
            exec_id,
            dataset_id,
            resource_id,
        )

        exec_status, stored_data_id = client.poll_execution(exec_id)

        # Delete upload after processing — API returns 409 if attempted while processing runs
        try:
            client.delete_upload(upload_id)
        except GeopfError as e:
            log.warning(
                "geopf: could not delete upload=%s dataset=%s resource=%s: %s",
                upload_id,
                dataset_id,
                resource_id,
                e,
            )
        upload_id = None  # mark cleaned up so the except block doesn't double-delete

        if exec_status != "SUCCESS":
            raise GeopfError(f"Processing execution ended with status {exec_status}")
        log.info(
            "geopf: stored_data=%s created dataset=%s resource=%s",
            stored_data_id,
            dataset_id,
            resource_id,
        )

    except GeopfTimeoutError:
        # Execution is still running on GeoPortail — deleting the upload would 409.
        # Leave both in place; a future retry or manual cleanup can finish the job.
        if upload_id:
            log.warning(
                "geopf: execution timed out, upload=%s left in place dataset=%s resource=%s",
                upload_id,
                dataset_id,
                resource_id,
            )
        raise
    except Exception:
        if upload_id:
            log.warning(
                "geopf: cleaning up orphaned upload=%s dataset=%s resource=%s",
                upload_id,
                dataset_id,
                resource_id,
            )
            try:
                client.delete_upload(upload_id)
            except GeopfError as e:
                log.warning("geopf: could not clean up upload=%s: %s", upload_id, e)
        raise

    client.tag_entity("stored_data", stored_data_id, datasheet_name)

    sync_metadata(dataset, client)

    fiche_url = (
        f"https://cartes.gouv.fr/tableau-de-bord/entrepots/{datastore_id}/donnees/{datasheet_name}"
    )
    _set_extras(
        dataset,
        resource,
        {
            "geopf:push:status": "done",
            "geopf:push:stored-data-id": stored_data_id,
            "geopf:push:last-synced-at": datetime.now(UTC).isoformat(),
        },
    )
    _set_dataset_extras(dataset, {"geopf:push:fiche-url": fiche_url})
    log.info(
        "geopf: push complete dataset=%s resource=%s fiche=%s", dataset_id, resource_id, fiche_url
    )


def _resource_filename(resource):
    if resource.fs_filename:
        return os.path.basename(resource.fs_filename)
    parsed = urlparse(resource.url)
    name = os.path.basename(parsed.path)
    return name or f"{resource.id}.gpkg"


def _open_resource_file(resource):
    """Return a context manager yielding an open binary file for the resource."""
    if resource.filetype == "file" and resource.fs_filename:
        return storages.resources.open(resource.fs_filename, "rb")
    return _download_to_tempfile(resource.url)


class _download_to_tempfile:
    """Download a remote URL to a temp file, yield it, clean up on exit."""

    def __init__(self, url):
        self.url = url
        self._tmp = None

    def __enter__(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False)
        try:
            with requests.get(self.url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_content(65536):
                    self._tmp.write(chunk)
            self._tmp.seek(0)
            return self._tmp
        except Exception:
            self._tmp.close()
            os.unlink(self._tmp.name)
            raise

    def __exit__(self, *_):
        if self._tmp:
            self._tmp.close()
            try:
                os.unlink(self._tmp.name)
            except OSError:
                pass


def sync_metadata(dataset, client):
    """Create or refresh the ISO 19115 metadata record for a dataset on Géoplateforme."""
    datasheet_name = str(dataset.id)
    xml = dataset_to_iso19115(dataset)
    metadata_id = dataset.extras.get("geopf:push:metadata-id")
    if metadata_id:
        client.update_metadata(metadata_id, xml)
        log.info("geopf: updated metadata=%s dataset=%s", metadata_id, dataset.id)
    else:
        metadata_id = client.upload_metadata(xml)
        log.info("geopf: uploaded metadata=%s dataset=%s", metadata_id, dataset.id)
        client.tag_entity("metadata", metadata_id, datasheet_name)
        _set_dataset_extras(dataset, {"geopf:push:metadata-id": metadata_id})
    return metadata_id


@job("geopf.sync-offerings", ignore_result=False)
def sync_geopf_offerings(self):
    """Periodic job: sync Géoplateforme offerings to udata resources for all pushed datasets."""
    if not current_app.config.get("GEOPF_TOKEN") or not current_app.config.get(
        "GEOPF_DATASTORE_ID"
    ):
        log.warning("geopf: GEOPF_TOKEN or GEOPF_DATASTORE_ID not configured, skipping sync")
        return

    client = GeopfClient()
    datasets = Dataset.objects(**{"extras__geopf:push:metadata-id__exists": True})
    log.info("geopf: syncing offerings for %d datasets", datasets.count())
    failures = []
    for dataset in datasets:
        try:
            n = sync_offerings_for_dataset(dataset, client)
            log.info("geopf: synced %d offerings for dataset=%s", n, dataset.id)
        except Exception as e:
            log.exception("geopf: offering sync failed for dataset=%s", dataset.id)
            failures.append(e)
    if failures:
        raise ExceptionGroup(f"geopf: sync failed for {len(failures)} dataset(s)", failures)


def sync_offerings_for_dataset(dataset, client) -> int:
    """Sync Géoplateforme offerings to udata resources. Returns count of live offerings."""
    stored_data_ids = {
        r.extras["geopf:push:stored-data-id"]
        for r in dataset.resources
        if r.extras.get("geopf:push:stored-data-id")
    }
    if not stored_data_ids:
        return 0

    live_offering_ids = set()
    for sd_id in stored_data_ids:
        for offering in client.list_offerings(sd_id):
            live_offering_ids.add(offering["_id"])
            _upsert_offering_resource(dataset, offering)

    # Remove resources whose offering no longer exists on GeoPortail
    for resource in list(dataset.resources):
        oid = resource.extras.get("geopf:offering:id")
        if oid and oid not in live_offering_ids:
            log.info(
                "geopf: removing resource=%s (offering=%s gone) dataset=%s",
                resource.id,
                oid,
                dataset.id,
            )
            dataset.remove_resource(resource)

    return len(live_offering_ids)


def _upsert_offering_resource(dataset, offering):
    offering_id = offering["_id"]
    service_type = offering.get("type", "")
    layer_name = offering.get("layer_name", "")
    url = _offering_url(offering)
    if not url:
        log.warning("geopf: offering=%s has no URL, skipping dataset=%s", offering_id, dataset.id)
        return

    title = f"Service {service_type} - {layer_name}" if layer_name else f"Service {service_type}"
    now = datetime.now(UTC).isoformat()
    existing = next(
        (r for r in dataset.resources if r.extras.get("geopf:offering:id") == offering_id),
        None,
    )

    if existing is None:
        resource = Resource(
            title=title,
            url=url,
            format=service_type.lower() if service_type else None,
            filetype="remote",
            type="api",
            extras={
                "geopf:offering:id": offering_id,
                "geopf:offering:last-synced-at": now,
            },
        )
        dataset.add_resource(resource)
        log.info(
            "geopf: added resource offering=%s type=%s layer=%s dataset=%s",
            offering_id,
            service_type,
            layer_name,
            dataset.id,
        )
    else:
        extras_update = {"geopf:offering:last-synced-at": now}
        if existing.url != url:
            existing.url = url
            dataset.update_resource(existing)
        _set_extras(dataset, existing, extras_update)


def _offering_url(offering: dict) -> str:
    urls = offering.get("urls") or []
    return urls[0].get("url", "") if urls else ""


def _set_dataset_extras(dataset, extras: dict):
    dataset.extras.update(extras)
    Dataset.objects(id=dataset.id).update_one(
        **{f"set__extras__{k}": v for k, v in extras.items()},
    )


def _set_extras(dataset, resource, extras: dict):
    """Update resource extras in-place and persist without reloading the full dataset."""
    resource = next((r for r in dataset.resources if str(r.id) == str(resource.id)), resource)
    resource.extras.update(extras)
    Dataset.objects(id=dataset.id, resources__id=resource.id).update_one(
        **{f"set__resources__S__extras__{k}": v for k, v in extras.items()},
    )
