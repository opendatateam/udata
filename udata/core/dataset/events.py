import datetime

import requests
from flask import current_app

from udata.event.values import EventMessageType
from udata.models import Dataset
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


@task(route="high.resource")
def publish(url, document, resource_id, action):
    if action == EventMessageType.DELETED:
        resource = None
    else:
        resource = serialize_resource_for_event(get_by(document.resources, "id", resource_id))
    payload = {
        "resource_id": str(resource_id),
        "dataset_id": str(document.id),
        "document": resource,
    }
    headers = {}
    if current_app.config["RESOURCES_ANALYSER_API_KEY"]:
        headers = {"Authorization": f"Bearer {current_app.config['RESOURCES_ANALYSER_API_KEY']}"}
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()


@Dataset.on_resource_added.connect
def publish_added_resource_message(sender, document, **kwargs):
    if current_app.config.get("PUBLISH_ON_RESOURCE_EVENTS") and current_app.config.get(
        "RESOURCES_ANALYSER_URI"
    ):
        publish.delay(
            f"{current_app.config.get('RESOURCES_ANALYSER_URI')}/api/resource/created/",
            document,
            kwargs["resource_id"],
            EventMessageType.CREATED,
        )


@Dataset.on_resource_updated.connect
def publish_updated_resource_message(sender, document, **kwargs):
    if current_app.config.get("PUBLISH_ON_RESOURCE_EVENTS") and current_app.config.get(
        "RESOURCES_ANALYSER_URI"
    ):
        publish.delay(
            f"{current_app.config.get('RESOURCES_ANALYSER_URI')}/api/resource/updated/",
            document,
            kwargs["resource_id"],
            EventMessageType.MODIFIED,
        )


@Dataset.on_resource_removed.connect
def publish_removed_resource_message(sender, document, **kwargs):
    if current_app.config.get("PUBLISH_ON_RESOURCE_EVENTS") and current_app.config.get(
        "RESOURCES_ANALYSER_URI"
    ):
        publish.delay(
            f"{current_app.config.get('RESOURCES_ANALYSER_URI')}/api/resource/deleted/",
            document,
            kwargs["resource_id"],
            EventMessageType.DELETED,
        )
