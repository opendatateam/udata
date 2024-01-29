'''
Some old dataset/reuse don't have a `private` field. It should be False by default.
'''
import logging

from udata.models import Reuse, Dataset

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

    log.info(f'Fixed {count} Reuse objects from private None to private False.')

    log.info('Processing Reuse.')

    datasets = Dataset.objects().no_cache().timeout(False)
    count = 0
    for dataset in datasets:
        if dataset.private == None: 
            dataset.private = False
            dataset.save()
            count += 1

    log.info(f'Fixed {count} Dataset objects from private None to private False.')

    log.info('Done')
