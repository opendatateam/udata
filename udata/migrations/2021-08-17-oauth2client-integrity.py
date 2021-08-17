'''
Remove Oauth2Client db integrity problems
'''
import logging

import mongoengine

from udata.api.oauth2 import OAuth2Client

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing Transfer objects.')

    clients = OAuth2Client.objects.no_cache().all()

    count = 0
    for client in clients:
        try:
            client.organization and client.organization.id
        except mongoengine.errors.DoesNotExist:
            count += 1
            client.organization = None
            client.save()

    log.info(f'Completed, modified {count} OAuth2Client objects')
