'''
Some old reuse don't have a `private` field. It should be False by default.
'''
import logging

from udata.models import Reuse

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing Reuse.')

    reuses = Reuse.objects().no_cache().timeout(False)
    count = 0
    for reuse in reuses:
        if reuse.private == None: 
            reuse.private = False
            reuse.save()
            count += 1

    log.info(f'Fixed {count} Reuses objects from private None to private False.')
    log.info('Done')
