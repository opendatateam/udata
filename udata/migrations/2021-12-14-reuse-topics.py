'''
Add a default topic to all reuses in db
'''
import logging

from udata.models import Reuse

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing Reuse.')

    reuses = Reuse.objects().no_cache().timeout(False)
    count = 0
    for reuse in reuses:
        reuse.topic = 'others'
        reuse.save()
        count += 1

    log.info(f'Modified {count} Reuses objects')
    log.info('Done')
