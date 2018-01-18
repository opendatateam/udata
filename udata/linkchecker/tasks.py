# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import uuid

from flask import current_app

from udata.models import Dataset
from udata.tasks import job
from udata.utils import get_by

from .checker import check_resource

log = logging.getLogger(__name__)


@job('check_resources')
def check_resources(self, number):
    '''Check <number> of URLs that have not been (recently) checked'''
    if not current_app.config.get('LINKCHECKING_ENABLED'):
        log.error('Link checking is disabled.')
        return

    base_pipeline = [
        {'$match': {'resources': {'$gt': []}}},
        {'$project': {'resources._id': True,
                      'resources.extras.check:date': True}},
        {'$unwind': '$resources'},
    ]
    # unchecked resources
    pipeline = base_pipeline + [
        {'$match': {'resources.extras.check:date': {'$eq': None}}},
        {'$limit': number}
    ]
    resources = list(Dataset.objects.aggregate(*pipeline))
    # not recently checked resources
    slots_left = number - len(resources)
    if slots_left:
        pipeline = base_pipeline + [
            {'$match': {'resources.extras.check:date': {'$ne': None}}},
            {'$sort': {'resources.extras.check:date': 1}},
            {'$limit': slots_left}
        ]
        resources += list(Dataset.objects.aggregate(*pipeline))

    nb_resources = len(resources)
    log.info('Checking %s resources...', nb_resources)
    for idx, dataset_resource in enumerate(resources):
        dataset_obj = Dataset.objects.get(id=dataset_resource['_id'])
        resource_id = dataset_resource['resources']['_id']
        rid = uuid.UUID(resource_id)
        resource_obj = get_by(dataset_obj.resources, 'id', rid)
        log.info('Checking resource %s (%s/%s)',
                 resource_id, idx + 1, nb_resources)
        if resource_obj.need_check():
            check_resource(resource_obj)
        else:
            log.info("--> Skipping this resource, cache is fresh enough.")
    log.info('Done.')
