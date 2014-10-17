# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from celery.utils.log import get_task_logger

from udata.tasks import celery

from udata.models import Dataset, DatasetIssue, FollowDataset, Activity, Metrics

log = get_task_logger(__name__)


@celery.task(name='purge-datasets')
def purge_datasets():
    for dataset in Dataset.objects(deleted__ne=None):
        log.info('Purging dataset "{0}"'.format(dataset))
        # Remove followers
        FollowDataset.objects(following=dataset).delete()
        # Remove issues
        DatasetIssue.objects(subject=dataset).delete()
        # Remove activity
        Activity.objects(related_to=dataset).delete()
        # Remove metrics
        Metrics.objects(object_id=dataset.id).delete()
        # Remove
        dataset.delete()
