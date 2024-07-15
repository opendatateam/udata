'''
The purpose here is to change the dates name in the dataset and resource model.
'''
import logging

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
    log.info(f'{result.modified_count} Community Resources processed for renaming.')
    result = community_resource_collection.update_many({}, {'$unset': { 'published': "" }})
    log.info(f'{result.modified_count} Community Resources processed for published removing.')

    result = dataset_collection.update_many({}, [{
        '$set': {
            'resources': {
                '$map': {
                    'input': '$resources',
                    'in': {
                        '$mergeObjects': ['$$this', { 'created_at_internal': '$$this.created_at', 'last_modified_internal': '$$this.modified' }]
                        }
                    }
                }
            },
        },
        { '$unset': 'resources.created_at'},
        { '$unset': 'resources.modified'},
        { '$unset': 'resources.published'}
    ])

    log.info('Completed.')
