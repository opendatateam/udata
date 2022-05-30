import logging
from uuid import UUID

from .models import get_resource
log = logging.getLogger(__name__)


def consume_message_resource_analysis(key, value):
    '''
    Reads a message and update the resource extras with the payload values.
    '''
    resource = get_resource(UUID(key))
    if resource:
        # TODO: add extra logic here
        for entry in value['data']:
            resource.extras[f'analysis:{entry}'] = value['data'][entry]
        resource.save()
    else:
        log.warn(f'No resource found for key {key}')
