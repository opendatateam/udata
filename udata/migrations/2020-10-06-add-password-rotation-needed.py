'''
The purpose here is to fill every user's password_rotation_needed field with False value.
after the PR []
'''
import logging

from udata.models import User

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing users.')

    users = User.objects().no_cache().timeout(False)
    for user in users:
        user['password_rotation_needed'] = False
        user.save()

    log.info('Completed.')
