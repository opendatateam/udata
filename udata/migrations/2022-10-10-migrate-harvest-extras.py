'''
Move identifying harvest fields from extras to dedicated harvest metadata fields.
Clean other extras set at harvest time, they will be re-created if needed.
'''
import logging

from mongoengine.errors import ValidationError
from udata.models import Dataset
from udata.core.dataset.models import HarvestDatasetMetadata

log = logging.getLogger(__name__)


def should_keep(extra):
    extras_to_remove = ['remote_url', 'dct:identifier', 'uri', 'ckan:name', 'ckan:source']
    if extra.startswith('harvest:') or extra.startswith('ods:') or extra in extras_to_remove:
        return False
    return True


def migrate(db):
    log.info('Processing Datasets.')

    datasets = Dataset.objects(__raw__={
            '$or': [
                {'extras.harvest:remote_id': {'$exists': True}},
                {'extras.harvest:domain': {'$exists': True}},
                {'extras.harvest:source_id': {'$exists': True}},
            ],
        }).no_cache().timeout(False)

    datasets_count = datasets.count()
    for dataset in datasets:
        if not dataset.harvest:
            dataset.harvest = HarvestDatasetMetadata()
        dataset.harvest.remote_id = dataset.extras.pop('harvest:remote_id', None)
        dataset.harvest.source_id = dataset.extras.pop('harvest:source_id', None)
        dataset.harvest.domain = dataset.extras.pop('harvest:domain', None)
        # Keep last_update for archiving reason
        dataset.harvest.last_update = dataset.extras.pop('harvest:last_update', None)
        # Keep any archived reason and date
        dataset.harvest.archived = dataset.extras.pop('harvest:archived', None)
        dataset.harvest.archived_at = dataset.extras.pop('harvest:archived_at', None)

        dataset.extras = {extra: dataset.extras[extra] for extra in dataset.extras
                          if should_keep(extra)}
        for resource in dataset.resources:
            resource.extras = {extra: resource.extras[extra] for extra in resource.extras
                               if should_keep(extra)}

        try:
            dataset.save()
        except ValidationError as e:
            log.error(f'Failed to save dataset {dataset.id}: {e}')

    log.info(f'Modified {datasets_count} datasets objects')
    log.info('Done')
