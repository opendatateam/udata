'''
Move identifying harvest fields from extras to dedicated harvest metadata fields.
Clean other extras set at harvest time, they will be re-created if needed.
'''
import logging

from mongoengine.errors import ValidationError
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
        dataset.harvest.remote_id = dataset.extras.pop('harvest:remote_id')
        dataset.harvest.source_id = dataset.extras.pop('harvest:source_id')
        dataset.harvest.domain = dataset.extras.pop('harvest:domain')
        # Keep any archived reason and date
        dataset.harvest.archived = dataset.extras.pop('harvest:archived')
        dataset.harvest.archived_at = dataset.extras.pop('harvest:archived_at')

        more_harvest_extras = ['remote_url', 'dct:identifier', 'uri']
        for key in dataset.extras:
            if key.startwith('harvest:') or key.startwith('ods:') or key in more_harvest_extras:
                dataset.extras.pop(key)

        for resource in dataset.resources:
            for key in dataset.resource.extras:
                if key.startwith('harvest:') or key.startwith('ods:'):
                    dataset.extras.pop(key)

        try:
            dataset.save()
        except ValidationError as e:
            log.error(f'Failed to save dataset {dataset.id}: {e}')

    log.info(f'Modified {datasets.count()} datasets objects')
    log.info('Done')
