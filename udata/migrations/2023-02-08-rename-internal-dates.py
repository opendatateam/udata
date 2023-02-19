'''
The purpose here is to change the dates name in the dataset and resource model.
'''
import logging

from mongoengine.connection import get_db
from udata.models import User

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing Dataset collection.')

    db = get_db()
    dataset_collection = db.dataset
    dataset_collection.update_many({}, {'$rename': {
        'created_at': 'created_at_internal',
        'last_modified': 'last_modified_internal'}})

    community_resource_collection = db.community_resource
    community_resource_collection.update_many({}, {'$rename': {
        'created_at': 'created_at_internal',
        'modified': 'last_modified_internal',
        'harvest.modified_at': 'harvest.last_modified'}})

    datasets = Dataset.objects(resources__0__exists=True)
    for dataset in datasets:
        log.info('Processing dataset %s', dataset.id)
        for resource in dataset.resources:
            resource.created_at_internal = resource.pop('created_at')
            resource.last_modified_internal = resource.pop('modified')
            log.info('Processing resource %s', resource.id)
            if resource.harvest and resource.harvest.modified_at:
                resource.harvest.last_modified = resource.harvest.pop('modified_at')
        dataset.save()

    log.info('Completed.')
