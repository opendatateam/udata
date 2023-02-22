'''
The purpose here is to change the dates name in the dataset and resource model.
'''
import logging
import pymongo

from mongoengine.connection import get_db
from udata.models import Dataset

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing Dataset collection.')

    db = get_db()
    dataset_collection = db.dataset
    result = dataset_collection.update_many({}, {'$rename': {
        'created_at': 'created_at_internal',
        'last_modified': 'last_modified_internal'}})
    log.info(f'{result.modified_count} Datasets processed.')

    community_resource_collection = db.community_resource
    result = community_resource_collection.update_many({}, {'$rename': {
        'created_at': 'created_at_internal',
        'modified': 'last_modified_internal'}})
    log.info(f'{result.modified_count} Community Resources processed.')

    for dataset in dataset_collection.find():
        log.info(dataset['_id'])
        resources = dataset.get('resources', [])
        for resource in resources:
            log.info('Processing resource %s', resource['_id'])
            resource['created_at_internal'] = resource.pop('created_at')
            if resource.get('modified', None):
                resource['last_modified_internal'] = resource.pop('modified')
            if resource.get('harvest', None):
                if resource['harvest'].get('modified_at', None):
                    resource['harvest']['last_modified'] = resource['harvest'].pop('modified_at')
        dataset_collection.update_one({'_id': dataset['_id']}, {'$set': {'resources': resources}})

    log.info('Completed.')
