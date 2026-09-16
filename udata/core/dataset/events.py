import datetime
from collections.abc import Callable
from typing import Any

import requests
from flask import current_app

from udata.core.dataset.doi import DOI_METADATA_FIELDS, update_doi
from udata.event.values import EventMessageType
from udata.models import Dataset, Organization
from udata.tasks import task
from udata.utils import get_by, to_iso_datetime


def serialize_resource_for_event(resource):
    resource_dict = {
        "id": str(resource.id),
        "url": resource.url,
        "format": resource.format,
        "title": resource.title,
        "schema": resource.schema.to_dict() if resource.schema else None,
        "description": resource.description,
        "filetype": resource.filetype,
        "type": resource.type,
        "mime": resource.mime,
        "filesize": resource.filesize,
        "checksum_type": resource.checksum.type if resource.checksum else None,
        "checksum_value": resource.checksum.value if resource.checksum else None,
        "created_at": to_iso_datetime(resource.created_at),
        "last_modified": to_iso_datetime(resource.last_modified),
    }
    extras = {}
    for key, value in resource.extras.items():
        extras[key] = to_iso_datetime(value) if isinstance(value, datetime.datetime) else value
    resource_dict.update({"extras": extras})
    if resource.harvest:
        harvest = {}
        for key, value in resource.harvest._data.items():
            harvest[key] = to_iso_datetime(value) if isinstance(value, datetime.datetime) else value
        resource_dict.update({"harvest": harvest})
    return resource_dict


def payload_for_resource(document: Any, resource_id: str | None) -> dict | None:
    if resource_id is None:  # On delete, there is no resource_id, and no need for a payload.
        return None
    resource: dict = serialize_resource_for_event(get_by(document.resources, id=resource_id))
    return {
        "resource_id": str(resource_id),
        "dataset_id": str(document.id),
        "document": resource,
    }


@task(route="high.resource")
def publish(url: str, document: Any, resource_id: str, action: str) -> None:
    method: Callable
    match action:
        case EventMessageType.CREATED:
            method = requests.post
        case EventMessageType.MODIFIED:
            method = requests.put
        case EventMessageType.DELETED:
            method = requests.delete
    payload: dict | None = payload_for_resource(document, resource_id)
    headers = {}
    if current_app.config["RESOURCES_ANALYSER_API_KEY"]:
        headers = {"Authorization": f"Bearer {current_app.config['RESOURCES_ANALYSER_API_KEY']}"}
    r = method(url, json=payload, headers=headers)
    r.raise_for_status()


# These handlers live here rather than next to `create_doi` because `udata.event` is imported
# by `search.init_app`, hence by every process. `udata.core.dataset.api`, which is what pulls
# `doi.py` in, is only loaded by `standalone()`: moving them would silence the sync in workers,
# where the harvester updates datasets in bulk.
@task(route="high.dataset")
def push_doi_metadata(dataset_id: str) -> None:
    dataset = Dataset.objects(id=dataset_id).first()
    # An organization can be dropped after the DOI was minted (transfer to a user, organization
    # deletion). DataCite then keeps the publisher it was given, which is the one that was true
    # when the DOI was minted.
    if dataset and dataset.doi and dataset.organization:
        update_doi(dataset)


@Dataset.on_update.connect
def update_doi_on_metadata_change(dataset, **kwargs) -> None:
    """Keep DataCite in sync with the metadata it records for an already minted DOI."""
    if dataset.doi and DOI_METADATA_FIELDS.intersection(kwargs.get("changed_fields", [])):
        push_doi_metadata.delay(str(dataset.id))


@Organization.on_update.connect
def update_doi_on_organization_rename(organization, **kwargs) -> None:
    """Renaming an organization changes the DataCite publisher of every DOI it produced.

    Saving an organization emits no `Dataset.on_update`, so the dataset watcher above cannot
    see this one.
    """
    if "name" not in kwargs.get("changed_fields", []):
        return
    for dataset in Dataset.objects(organization=organization, doi__ne=None).only("id"):
        push_doi_metadata.delay(str(dataset.id))


@Dataset.on_resource_added.connect
def publish_added_resource_message(sender, document, **kwargs) -> None:
    if current_app.config.get("PUBLISH_ON_RESOURCE_EVENTS") and current_app.config.get(
        "RESOURCES_ANALYSER_URI"
    ):
        publish.delay(
            f"{current_app.config.get('RESOURCES_ANALYSER_URI')}/api/resources/",
            document,
            kwargs["resource_id"],
            EventMessageType.CREATED,
        )


@Dataset.on_resource_updated.connect
def publish_updated_resource_message(sender, document, **kwargs) -> None:
    if current_app.config.get("PUBLISH_ON_RESOURCE_EVENTS") and current_app.config.get(
        "RESOURCES_ANALYSER_URI"
    ):
        resource_id: str = kwargs["resource_id"]
        publish.delay(
            f"{current_app.config.get('RESOURCES_ANALYSER_URI')}/api/resources/{resource_id}",
            document,
            resource_id,
            EventMessageType.MODIFIED,
        )


@Dataset.on_resource_removed.connect
def publish_removed_resource_message(sender, document, **kwargs) -> None:
    if current_app.config.get("PUBLISH_ON_RESOURCE_EVENTS") and current_app.config.get(
        "RESOURCES_ANALYSER_URI"
    ):
        resource_id: str = kwargs["resource_id"]
        publish.delay(
            f"{current_app.config.get('RESOURCES_ANALYSER_URI')}/api/resources/{resource_id}",
            document,
            None,
            EventMessageType.DELETED,
        )
