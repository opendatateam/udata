import logging
import os
import tempfile
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID

from flask import current_app

from udata.core import storages
from udata.core.dataset.models import Dataset, Resource
from udata.core.storages.utils import md5
from udata.core.user.models import User
from udata.http import ssrf_session
from udata.tasks import task
from udata.utils import get_by

from .auth import resolve_access_token
from .client import (
    POLL_TIMEOUT,
    GeopfClient,
    GeopfError,
    GeopfReauthRequired,
    GeopfTimeoutError,
)
from .metadata import dataset_to_iso19115
from .models import (
    GeopfDatasetMetadata,
    GeopfDatasetPullMetadata,
    GeopfDatasetPushMetadata,
    GeopfResourceMetadata,
    GeopfResourceOfferingMetadata,
    GeopfResourcePushMetadata,
    dataset_push_metadata,
    resource_offering_metadata,
    resource_push_metadata,
)
from .srs import DEFAULT_SRS, detect_srs

log = logging.getLogger(__name__)


@task(name="geopf.push_resource", bind=True, ignore_result=False)
def push_resource_to_geopf(
    self,
    dataset_id: str,
    resource_id: str,
    user_id: str | None = None,
    datastore_id: str | None = None,
    access_token: str | None = None,
) -> None:
    """Push a resource (format in `GEOPF_PUSHABLE_FORMATS`) to Géoplateforme as the acting user.

    Pass `user_id` for the normal path (their stored `GeopfToken` is looked
    up and refreshed as needed). `access_token` is an ops/CLI-only escape
    hatch that bypasses stored-token resolution entirely with a raw token.
    """
    log.info(
        "geopf: starting push dataset=%s resource=%s user=%s", dataset_id, resource_id, user_id
    )
    dataset = Dataset.objects.get(id=dataset_id)
    resource = get_by(dataset.resources, id=UUID(resource_id))
    if resource is None:
        log.error("geopf: resource not found dataset=%s resource=%s", dataset_id, resource_id)
        return

    if (
        not resource.format
        or resource.format.lower() not in current_app.config["GEOPF_PUSHABLE_FORMATS"]
    ):
        return

    # A dataset lives in exactly one entrepôt on geopf (the fiche dashboard URL
    # itself is scoped to one datastore), so once a dataset has pushed before,
    # every subsequent push reuses that datastore rather than re-resolving one.
    existing_datastore_id = dataset_push_metadata(dataset).datastore_id
    if existing_datastore_id:
        if datastore_id and datastore_id != existing_datastore_id:
            log.warning(
                "geopf: dataset=%s is already pushed to datastore=%s, ignoring "
                "requested datastore=%s",
                dataset_id,
                existing_datastore_id,
                datastore_id,
            )
        datastore_id = existing_datastore_id
    if not datastore_id:
        log.warning(
            "geopf: no datastore_id provided, skipping push dataset=%s resource=%s",
            dataset_id,
            resource_id,
        )
        return

    if not access_token:
        user = User.objects.get(id=user_id)
        try:
            # The token must outlive the pipeline: up to one full poll for
            # checks plus one for processing.
            poll_timeout = current_app.config.get("GEOPF_POLL_TIMEOUT", POLL_TIMEOUT)
            access_token = resolve_access_token(user=user, min_validity=2 * poll_timeout)
        except GeopfReauthRequired as e:
            log.error(
                "geopf: no usable geopf token for user=%s dataset=%s resource=%s: %s",
                user_id,
                dataset_id,
                resource_id,
                e,
            )
            set_resource_push_metadata(dataset, resource, status="error", error=str(e))
            raise

    pending = {"status": "pending", "error": None}
    if self.request.id:  # None on synchronous CLI runs
        pending["task_id"] = self.request.id
    set_resource_push_metadata(dataset, resource, **pending)

    client = GeopfClient(token=access_token, datastore_id=datastore_id)
    try:
        _run_pipeline(dataset, resource, datastore_id, client)
    except GeopfTimeoutError as e:
        log.exception("geopf: pipeline timed out dataset=%s resource=%s", dataset_id, resource_id)
        set_resource_push_metadata(dataset, resource, status="timeout", error=str(e))
        raise
    except Exception as e:
        log.exception("geopf: pipeline failed dataset=%s resource=%s", dataset_id, resource_id)
        set_resource_push_metadata(dataset, resource, status="error", error=str(e))
        raise

    # Pin only after success, so a failed first push can't lock the dataset
    # onto a bad datastore.
    set_dataset_push_metadata(dataset, datastore_id=datastore_id)


def _run_pipeline(dataset, resource, datastore_id: str, client) -> None:
    datasheet_name = str(dataset.id)
    stored_data_name = f"_{resource.id}"
    filename = _resource_filename(resource)
    dataset_id = dataset.id
    resource_id = resource.id

    upload_id = None
    stored_data_id = None

    try:
        with _open_resource_file(resource) as f:
            file_md5 = md5(f)
            f.seek(0)

            srs = detect_srs(f, resource.format) or DEFAULT_SRS
            log.debug("geopf: using srs=%s dataset=%s resource=%s", srs, dataset_id, resource_id)

            upload_id = client.create_upload(
                name=stored_data_name,
                description=dataset.title,
                srs=srs,
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

        exec_id = client.launch_processing(upload_id, stored_data_name, srs=srs)
        log.info(
            "geopf: launched processing execution=%s dataset=%s resource=%s",
            exec_id,
            dataset_id,
            resource_id,
        )

        exec_status, stored_data_id = client.poll_execution(exec_id)

        # Delete upload after processing; API returns 409 if attempted while processing runs
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
        # Checks or processing still running on GeoPortail; deleting the upload would 409.
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

    url = fiche_url(datastore_id, datasheet_name)
    set_resource_push_metadata(
        dataset,
        resource,
        status="done",
        stored_data_id=stored_data_id,
        last_synced_at=datetime.now(UTC),
    )
    set_dataset_push_metadata(dataset, fiche_url=url)
    log.info("geopf: push complete dataset=%s resource=%s fiche=%s", dataset_id, resource_id, url)


def fiche_url(datastore_id: str, datasheet_name: str) -> str:
    """URL of the datasheet's fiche on the cartes.gouv.fr dashboard."""
    base = current_app.config["GEOPF_DASHBOARD_BASE"]
    return f"{base}/tableau-de-bord/entrepots/{datastore_id}/donnees/{datasheet_name}"


def _resource_filename(resource) -> str:
    if resource.fs_filename:
        return os.path.basename(resource.fs_filename)
    parsed = urlparse(resource.url)
    name = os.path.basename(parsed.path)
    return name or f"{resource.id}.gpkg"


def _open_resource_file(resource):
    """Return a context manager yielding an open binary file for the resource."""
    if resource.filetype == "file" and resource.fs_filename:
        return storages.resources.open(resource.fs_filename, "rb")
    return _DownloadToTempfile(resource.url)


class _DownloadToTempfile:
    """Download a remote URL to a temp file, yield it, clean up on exit.

    `self.url` is user-controlled (remote resource URL) and this fetch runs
    on the worker, so it goes through the SSRF-hardened session rather than
    a bare `requests.get`.
    """

    def __init__(self, url: str):
        self.url = url
        self._tmp = None

    def __enter__(self):
        max_size = current_app.config["GEOPF_MAX_REMOTE_FILE_SIZE"]
        self._tmp = tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False)
        try:
            with ssrf_session().get(self.url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                size = 0
                for chunk in resp.iter_content(65536):
                    size += len(chunk)
                    if size > max_size:
                        raise GeopfError(
                            f"Remote file at {self.url} exceeds "
                            f"GEOPF_MAX_REMOTE_FILE_SIZE ({max_size} bytes)"
                        )
                    self._tmp.write(chunk)
            self._tmp.seek(0)
            return self._tmp
        except Exception:
            self._tmp.close()
            os.unlink(self._tmp.name)
            raise

    def __exit__(self, *_) -> None:
        if self._tmp:
            self._tmp.close()
            try:
                os.unlink(self._tmp.name)
            except OSError:
                pass


def sync_metadata(dataset, client) -> str:
    """Create or refresh the ISO 19115 metadata record for a dataset on Géoplateforme."""
    datasheet_name = str(dataset.id)
    xml = dataset_to_iso19115(dataset, datastore_id=client.datastore)
    metadata_id = dataset_push_metadata(dataset).metadata_id
    if metadata_id:
        client.update_metadata(metadata_id, xml)
        log.info("geopf: updated metadata=%s dataset=%s", metadata_id, dataset.id)
    else:
        metadata_id = client.upload_metadata(xml)
        log.info("geopf: uploaded metadata=%s dataset=%s", metadata_id, dataset.id)
        client.tag_entity("metadata", metadata_id, datasheet_name)
        set_dataset_push_metadata(dataset, metadata_id=metadata_id)
    return metadata_id


@task(name="geopf.pull_offerings", bind=True, ignore_result=False)
def pull_offerings_from_geopf(
    self, dataset_id: str, user_id: str | None = None, access_token: str | None = None
) -> int:
    """Pull Géoplateforme offerings into resources for a dataset, as the acting user.

    Pass `user_id` for the normal path (their stored `GeopfToken` is looked
    up and refreshed as needed). `access_token` is an ops/CLI-only escape
    hatch that bypasses stored-token resolution entirely with a raw token.
    """
    dataset = Dataset.objects.get(id=dataset_id)

    if not access_token:
        user = User.objects.get(id=user_id)
        try:
            access_token = resolve_access_token(user=user)
        except GeopfReauthRequired as e:
            log.error(
                "geopf: no usable geopf token for user=%s dataset=%s: %s", user_id, dataset_id, e
            )
            set_dataset_pull_metadata(dataset, status="error", error=str(e))
            raise

    pending = {"status": "pending", "error": None}
    if self.request.id:  # None on synchronous CLI runs
        pending["task_id"] = self.request.id
    set_dataset_pull_metadata(dataset, **pending)

    try:
        n = pull_offerings_for_dataset(dataset, access_token)
    except Exception as e:
        log.exception("geopf: offering pull failed for dataset=%s", dataset_id)
        set_dataset_pull_metadata(dataset, status="error", error=str(e))
        raise

    set_dataset_pull_metadata(dataset, status="done", last_synced_at=datetime.now(UTC))
    return n


def pull_offerings_for_dataset(dataset, token) -> int:
    """Pull Géoplateforme offerings into udata resources. Returns count of live offerings.

    `token` is a geopf access token for the acting user. A dataset lives in
    exactly one entrepôt (`dataset.geopf.push.datastore_id`); every one of
    its push resources' `resource.geopf.push.stored_data_id` is looked up
    within that same datastore.
    """
    datastore_id = dataset_push_metadata(dataset).datastore_id
    stored_data_ids = {
        push.stored_data_id
        for r in dataset.resources
        if (push := resource_push_metadata(r)).stored_data_id
    }
    if not datastore_id or not stored_data_ids:
        return 0

    client = GeopfClient(token=token, datastore_id=datastore_id)
    live_offering_ids = set()
    for sd_id in stored_data_ids:
        for offering in client.list_offerings(sd_id):
            live_offering_ids.add(offering["_id"])
            _upsert_offering_resource(dataset, offering)

    # Remove resources whose offering no longer exists on GeoPortail
    for resource in list(dataset.resources):
        oid = resource_offering_metadata(resource).id
        if oid and oid not in live_offering_ids:
            log.info(
                "geopf: removing resource=%s (offering=%s gone) dataset=%s",
                resource.id,
                oid,
                dataset.id,
            )
            dataset.remove_resource(resource)

    return len(live_offering_ids)


def _upsert_offering_resource(dataset, offering: dict) -> None:
    offering_id = offering["_id"]
    service_type = offering.get("type", "")
    layer_name = offering.get("layer_name", "")
    url = _offering_url(offering)
    if not url:
        log.warning("geopf: offering=%s has no URL, skipping dataset=%s", offering_id, dataset.id)
        return

    title = f"Service {service_type} - {layer_name}" if layer_name else f"Service {service_type}"
    now = datetime.now(UTC)
    existing = next(
        (r for r in dataset.resources if resource_offering_metadata(r).id == offering_id),
        None,
    )

    if existing is None:
        resource = Resource(
            title=title,
            url=url,
            format=service_type.lower() if service_type else None,
            filetype="remote",
            type="api",
            geopf=GeopfResourceMetadata(
                offering=GeopfResourceOfferingMetadata(id=offering_id, last_synced_at=now)
            ),
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
        if existing.url != url:
            existing.url = url
            dataset.update_resource(existing)
        set_resource_offering_metadata(dataset, existing, last_synced_at=now)


def _offering_url(offering: dict) -> str:
    urls = offering.get("urls") or []
    return urls[0].get("url", "") if urls else ""


def _set_metadata_section(
    container, section: str, factory, fields: dict, query, path_prefix: str
) -> None:
    """Set fields on `container.geopf.<section>` atomically; `None` unsets rather than nulls."""
    doc = getattr(container.geopf, section)
    if doc is None:
        doc = factory()
        setattr(container.geopf, section, doc)

    ops = {}
    for key, value in fields.items():
        setattr(doc, key, value)
        path = f"{path_prefix}__{section}__{key}"
        ops[f"{'unset' if value is None else 'set'}__{path}"] = True if value is None else value
    query.update_one(**ops)


def set_dataset_push_metadata(dataset, **fields) -> None:
    if dataset.geopf is None:
        dataset.geopf = GeopfDatasetMetadata()
    _set_metadata_section(
        dataset, "push", GeopfDatasetPushMetadata, fields, Dataset.objects(id=dataset.id), "geopf"
    )


def set_dataset_pull_metadata(dataset, **fields) -> None:
    if dataset.geopf is None:
        dataset.geopf = GeopfDatasetMetadata()
    _set_metadata_section(
        dataset, "pull", GeopfDatasetPullMetadata, fields, Dataset.objects(id=dataset.id), "geopf"
    )


def set_resource_push_metadata(dataset, resource, **fields) -> None:
    resource = get_by(dataset.resources, id=resource.id)
    if resource.geopf is None:
        resource.geopf = GeopfResourceMetadata()
    _set_metadata_section(
        resource,
        "push",
        GeopfResourcePushMetadata,
        fields,
        Dataset.objects(id=dataset.id, resources__id=resource.id),
        "resources__S__geopf",
    )


def set_resource_offering_metadata(dataset, resource, **fields) -> None:
    resource = get_by(dataset.resources, id=resource.id)
    if resource.geopf is None:
        resource.geopf = GeopfResourceMetadata()
    _set_metadata_section(
        resource,
        "offering",
        GeopfResourceOfferingMetadata,
        fields,
        Dataset.objects(id=dataset.id, resources__id=resource.id),
        "resources__S__geopf",
    )
