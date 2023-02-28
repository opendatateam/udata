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
    log.info(f'{result.modified_count} Community Resources processed.')

    for dataset in dataset_collection.find():
    # result = dataset_collection.update_many({}, [{
    #     '$set': {
    #         'resources': {
    #             '$map': {
    #                 'input': '$resources',
    #                 'in': {
    #                     '$mergeObjects': ['$$this', { 'created_at_internal': '$$this.created_at', 'last_modified_internal': '$$this.modified' }]
    #                     }
    #                 }
    #             }
    #         },
    #     },
    #     { '$unset': 'resources.created_at'},
    #     { '$unset': 'resources.modified'}
    # ])
    # for dataset in datasets:
        # for resource in dataset.resources:
        #     breakpoint()
        #     resource.created_at_internal = resource.pop('created_at')
        #     resource.last_modified_internal = resource.pop('modified')
        #     log.info('Processing resource %s', resource.id)
        #     if resource.harvest and resource.harvest.modified_at:
        #         resource.harvest.last_modified = resource.harvest.pop('modified_at')
        # dataset.save()

    log.info('Completed.')

# db.students3.insertMany( [
#    { "_id" : 1, "resources" : [ {"created_at": ISODate("2019-01-01T00:00:00Z"), "modified": ISODate("2021-01-01T00:00:00Z")}, {"created_at": ISODate("2018-01-01T00:00:00Z"), "modified": ISODate("2022-01-01T00:00:00Z")} ] },
#    { "_id" : 2, "resources" : [ {"created_at": ISODate("2019-01-01T00:00:00Z"), "modified": ISODate("2021-01-01T00:00:00Z")}, {"created_at": ISODate("2018-01-01T00:00:00Z"), "modified": ISODate("2022-01-01T00:00:00Z")} ] },
# ] );

# db.students3.updateMany(
#    { },
#    [{
#     '$set': {
#         'resources': {
#             '$map': {
#                 'input': '$resources',
#                 'in': {
#                     '$mergeObjects': ['$$this', { 'created_at_internal': '$$this.created_at', 'last_modified_internal': '$$this.modified' }]
#                 }
#             }
#         }
#     },
#     },
#     { '$unset': 'resources.created_at'},
#     { '$unset': 'resources.modified'}
#     ])

# db.students3.updateMany(
#    { },
#    [
#      { $unset: "modified" }
#    ]
# )
