import datetime
from flask import current_app
from udata.utils import to_iso_datetime, get_by
from udata.models import Dataset
from udata.event import KafkaMessageType
from udata.tasks import task
from udata.event.producer import produce


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
    resource = serialize_resource_for_event(get_by(document.resources, 'id', resource_id))
    produce(topic=topic, id=str(document.id), message_type=message_type, document=resource)


@Dataset.on_resource_added.connect
def publish_add_resource_message(sender, document, **kwargs):
    if current_app.config.get('PUBLISH_ON_RESOURCE_EVENTS'):
        publish.delay(document, kwargs['resource_id'], 'resource.created', KafkaMessageType.RESOURCE_CREATED)


@Dataset.on_resource_updated.connect
def publish_update_resource_message(sender, document, **kwargs):
    if current_app.config.get('PUBLISH_ON_RESOURCE_EVENTS'):
        publish.delay(document, kwargs['resource_id'], 'resource.modified', KafkaMessageType.RESOURCE_MODIFIED)
