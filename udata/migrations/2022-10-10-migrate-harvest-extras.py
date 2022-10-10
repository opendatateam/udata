'''
Move identifying harvest fields from extras to dedicated harvest metadata fields.
Ignore other extras set at harvest time, they will be re-created if needed.
'''
import logging

from udata.models import Dataset
from udata.core.dataset.models import HarvestDatasetMetadata

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing Datasets.')

    datasets = Dataset.objects(__raw__={
            '$or': [
                {'extras.harvest:remote_id': {'$exists': True}},
                {'extras.harvest:domain': {'$exists': True}},
                {'extras.harvest:source_id': {'$exists': True}},
            ],
        }).no_cache().timeout(False)

    for dataset in datasets:
        if not dataset.harvest:
            dataset.harvest = HarvestDatasetMetadata()
        dataset.harvest.remote_id = dataset.extras.get('harvest:remote_id')
        dataset.harvest.source_id = dataset.extras.get('harvest:source_id')
        dataset.harvest.domain = dataset.extras.get('harvest:domain')
        dataset.save()

    log.info(f'Modified {datasets.count()} datasets objects')
    log.info('Done')
