'''
The purpose here is to update every resource's metadata 'schema' name.
'''
import logging
from udata.core.reuse.models import Reuse

from udata.models import Dataset, Reuse

log = logging.getLogger(__name__)

UNUSED_BADGES = [
    'dataconnexions-5-candidate',
    'dataconnexions-5-laureate',
    'dataconnexions-6-candidate',
    'dataconnexions-6-laureate',
    'covid-19',
    'c3',
    'nec',
    'openfield16',
    'bal'
]

def migrate(db):
    log.info('Processing datasets.')

    datasets = Dataset.objects().no_cache().timeout(False)
    for dataset in datasets:
        save_res = False
        for badge in dataset.__badges__:
            if badge in UNUSED_BADGES:
                del dataset.__badges__[badge]
                save_res = True
        if save_res:
            try:
                dataset.save()
            except Exception as e:
                log.warning(e)
                pass

    log.info('Processing reuses.')

    reuses = Reuse.objects().no_cache().timeout(False)
    for reuse in reuses:
        save_res = False
        for badge in reuse.__badges__:
            if badge in UNUSED_BADGES:
                del reuse.__badges__[badge]
                save_res = True
        if save_res:
            try:
                reuse.save()
            except Exception as e:
                log.warning(e)
                pass

    log.info('Completed.')
