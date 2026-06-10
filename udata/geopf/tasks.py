import logging
import os
import tempfile
from datetime import UTC, datetime
from urllib.parse import urlparse

import requests
from flask import current_app

from udata.core import storages
from udata.core.dataset.models import Dataset
from udata.tasks import task

from .client import GeopfClient, GeopfError, md5_of_file
from .metadata import dataset_to_iso19115

log = logging.getLogger(__name__)


@task(name="geopf.push_resource")
def push_resource_to_geopf(dataset_id, resource_id):
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

    _set_extras(dataset, resource, {"geopf_status": "pending"})

    try:
        _run_pipeline(dataset, resource, datastore_id)
    except Exception as e:
        log.exception("geopf: pipeline failed dataset=%s resource=%s", dataset_id, resource_id)
        _set_extras(dataset, resource, {"geopf_status": "error", "geopf_error": str(e)})


def _run_pipeline(dataset, resource, datastore_id):
    client = GeopfClient()
    datasheet_name = str(dataset.id)
    stored_data_name = str(resource.id)
    filename = _resource_filename(resource)
    dataset_id = dataset.id
    resource_id = resource.id

    upload_id = None
    stored_data_id = None

    try:
        with _open_resource_file(resource) as f:
            md5 = md5_of_file(f)

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
            client.push_md5(upload_id, filename, md5)
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

    xml = dataset_to_iso19115(dataset)
    metadata_id = dataset.extras.get("geopf_metadata_id")
    if metadata_id:
        client.update_metadata(metadata_id, xml)
        log.info("geopf: updated metadata=%s dataset=%s", metadata_id, dataset_id)
    else:
        metadata_id = client.upload_metadata(xml)
        log.info("geopf: uploaded metadata=%s dataset=%s", metadata_id, dataset_id)
        client.tag_entity("metadata", metadata_id, datasheet_name)
        _set_dataset_extras(dataset, {"geopf_metadata_id": metadata_id})

    fiche_url = (
        f"https://cartes.gouv.fr/tableau-de-bord/entrepots/{datastore_id}/donnees/{datasheet_name}"
    )
    _set_extras(
        dataset,
        resource,
        {
            "geopf_status": "done",
            "geopf_datasheet_name": datasheet_name,
            "geopf_stored_data_id": stored_data_id,
            "geopf_last_synced_at": datetime.now(UTC).isoformat(),
            "geopf_fiche_url": fiche_url,
        },
    )
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


def _set_dataset_extras(dataset, extras: dict):
    for k, v in extras.items():
        dataset.extras[k] = v
    Dataset.objects(id=dataset.id).update_one(
        **{f"set__extras__{k}": v for k, v in extras.items()},
    )


def _set_extras(dataset, resource, extras: dict):
    """Update resource extras in-place and persist without reloading the full dataset."""
    resource = next((r for r in dataset.resources if str(r.id) == str(resource.id)), resource)
    for k, v in extras.items():
        resource.extras[k] = v
    Dataset.objects(id=dataset.id, resources__id=resource.id).update_one(
        **{f"set__resources__S__extras__{k}": v for k, v in extras.items()},
    )
