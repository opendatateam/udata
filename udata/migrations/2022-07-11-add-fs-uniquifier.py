'''
Add fs_uniquifier to all users in db
'''
import logging
import uuid

from udata.models import User

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing Users.')

    users = User.objects().no_cache().timeout(False)
    count = 0
    for user in users:
        if not user.fs_uniquifier:
            user.fs_uniquifier = uuid.uuid4().hex
            user.save()
            count += 1

    log.info(f'Modified {count} User objects')
    log.info('Done')
