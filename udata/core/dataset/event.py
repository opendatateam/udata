import logging
from uuid import UUID

from .models import get_resource
log = logging.getLogger(__name__)


def consume_message_resource_analysed(key, value):
    '''
    Reads a message and update the resource extras with the payload values.
    '''
    log.info("Consuming message analysed")
    resource = get_resource(UUID(key))
    if resource:
        # TODO: add extra logic here
        for entry in value['value']:
            if value['value'][entry]:
                resource.extras[f'analysis:{entry}'] = value['value'][entry]
        resource.save()
    else:
        log.warn(f'No resource found for key {key}')


def consume_message_resource_stored(key, value):
    '''
    Reads a message and update the resource extras with the payload values.
    '''
    log.info("Consuming message stored")
    resource = get_resource(UUID(key))
    if resource:
        resource.extras['stored:location'] = '/'.join([
            value['value']['location']['netloc'],
            value['value']['location']['bucket'],
            value['value']['location']['key']])
        resource.save()
    else:
        log.warn(f'No resource found for key {key}')


def consume_message_resource_checked(key, value):
    '''
    Reads a message and update the resource extras with the payload values.
    '''
    log.info("Consuming message checked")
    resource = get_resource(UUID(key))
    if resource:
        if value['value']['status']:
            resource.extras['checked:status'] = value['value']['status']
        if value['meta']['check_date']:
            resource.extras['checked:check_date'] = value['meta']['check_date']
        resource.save()
    else:
        log.warn(f'No resource found for key {key}')
