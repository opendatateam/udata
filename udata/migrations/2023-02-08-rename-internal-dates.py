'''
The purpose here is to change the dates name in the dataset and resource model.
'''
import logging

from mongoengine.connection import get_db

log = logging.getLogger(__name__)


def migrate(db):
    log.info('Processing Dataset collection.')

    db = get_db()
    dataset_collection = db.dataset
    dataset_collection.update_many({}, {'$rename': {
        'created_at': 'created_at_internal',
        'last_modified': 'last_modified_internal',
        'resource.created_at': 'resource.created_at_internal',
        'resource.modified': 'resource.last_modified_internal'}})

    community_resource_collection = db.community_resource
    community_resource_collection.update_many({}, {'$rename': {
        'created_at': 'created_at_internal',
        'modified': 'last_modified_internal'}})

    log.info('Completed.')
