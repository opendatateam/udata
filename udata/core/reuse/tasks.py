# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from celery.utils.log import get_task_logger

from udata.tasks import job

from udata.models import Reuse, ReuseIssue, FollowReuse, Activity, Metrics

log = get_task_logger(__name__)


@job('purge-reuses')
def purge_reuses():
    for reuse in Reuse.objects(deleted__ne=None):
        log.info('Purging reuse "{0}"'.format(reuse))
        # Remove followers
        FollowReuse.objects(following=reuse).delete()
        # Remove issues
        ReuseIssue.objects(subject=reuse).delete()
        # Remove activity
        Activity.objects(related_to=reuse).delete()
        # Remove metrics
        Metrics.objects(object_id=reuse.id).delete()
        reuse.delete()
