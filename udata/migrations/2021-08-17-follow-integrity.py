'''
Remove Follow integrity problems
⚠️ long migration
'''
import logging

import mongoengine

from udata.models import Follow

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing Follow references.')

    count = 0
    follows = Follow.objects(following__ne=None).no_cache().all()
    for follow in follows:
        try:
            follow.following.id
        except mongoengine.errors.DoesNotExist:
            count += 1
            follow.delete()

    log.info(f'Delete {count} Follow objects')
