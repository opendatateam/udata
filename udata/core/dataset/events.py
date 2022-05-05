import datetime
from udata.utils import to_iso_datetime, get_by
from udata.models import Dataset
from udata.event import KafkaMessageType
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


@Dataset.on_resource_added.connect
def publish_add_resource_message(sender, document, **kwargs):
    resource = serialize_resource_for_event(get_by(document.resources, 'id', kwargs['resource_id']))
    produce(topic='resource:created', id=str(document.id), message_type=KafkaMessageType.RESOURCE_CREATED, document=resource)


@Dataset.on_resource_updated.connect
def publish_update_resource_message(sender, document, **kwargs):
    resource = serialize_resource_for_event(get_by(document.resources, 'id', kwargs['resource_id']))
    produce(topic='resource:modified', id=str(document.id), message_type=KafkaMessageType.RESOURCE_MODIFIED, document=resource)
