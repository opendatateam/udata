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
        for badge in UNUSED_BADGES:
            if dataset.get_badge(badge):
                dataset.remove_badge(badge)

    log.info('Processing reuses.')

    reuses = Reuse.objects().no_cache().timeout(False)
    for reuse in reuses:
        for badge in UNUSED_BADGES:
            if reuse.get_badge(badge):
                reuse.remove_badge(badge)

    log.info('Completed.')
