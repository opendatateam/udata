import datetime
from flask import current_app
from udata.utils import to_iso_datetime, get_by
from udata.models import Dataset
from udata.tasks import task
from udata.event.producer import produce
from udata.event.values import KafkaMessageType, KafkaTopic


def serialize_resource_for_event(resource):
    resource_dict = {
        'id': str(resource.id),
        'url': resource.url,
        'format': resource.format,
        'title': resource.title,
        'schema': resource.schema,
        'description': resource.description,
        'filetype': resource.filetype,
        'type': resource.type,
        'mime': resource.mime,
        'filesize': resource.filesize,
        'checksum_type': resource.checksum.type if resource.checksum else None,
        'checksum_value': resource.checksum.value if resource.checksum else None,
        'created_at': to_iso_datetime(resource.created_at),
        'modified': to_iso_datetime(resource.modified),
        'published': to_iso_datetime(resource.published)
    }
    extras = {}
    for key, value in resource.extras.items():
        extras[key] = to_iso_datetime(value) if isinstance(value, datetime.datetime) else value
    resource_dict.update({'extras': extras})
    return resource_dict


@task(route='high.resource')
def publish(document, resource_id, topic, message_type):
    if message_type == KafkaMessageType.RESOURCE_DELETED:
        resource = None
    else:
        resource = serialize_resource_for_event(get_by(document.resources, 'id', resource_id))
    produce(topic=topic.value, id=str(resource_id), message_type=message_type, document=resource, dataset_id=str(document.id))


@Dataset.on_resource_added.connect
def publish_added_resource_message(sender, document, **kwargs):
    if current_app.config.get('PUBLISH_ON_RESOURCE_EVENTS'):
        publish.delay(document, kwargs['resource_id'], KafkaTopic.RESOURCE_CREATED, KafkaMessageType.RESOURCE_CREATED)


@Dataset.on_resource_updated.connect
def publish_updated_resource_message(sender, document, **kwargs):
    if current_app.config.get('PUBLISH_ON_RESOURCE_EVENTS'):
        publish.delay(document, kwargs['resource_id'], KafkaTopic.RESOURCE_MODIFIED, KafkaMessageType.RESOURCE_MODIFIED)


@Dataset.on_resource_removed.connect
def publish_removed_resource_message(sender, document, **kwargs):
    if current_app.config.get('PUBLISH_ON_RESOURCE_EVENTS'):
        publish.delay(document, kwargs['resource_id'], KafkaTopic.RESOURCE_DELETED, KafkaMessageType.RESOURCE_DELETED)
