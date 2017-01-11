# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.models import Activity, Metrics, Issue, Discussion, Follow
from udata.tasks import get_logger, job, task

from .models import Reuse

log = get_logger(__name__)


@job('purge-reuses')
def purge_reuses(self):
    for reuse in Reuse.objects(deleted__ne=None):
        log.info('Purging reuse "{0}"'.format(reuse))
        # Remove followers
        Follow.objects(following=reuse).delete()
        # Remove issues
        Issue.objects(subject=reuse).delete()
        # Remove discussions
        Discussion.objects(subject=reuse).delete()
        # Remove activity
        Activity.objects(related_to=reuse).delete()
        # Remove metrics
        Metrics.objects(object_id=reuse.id).delete()
        reuse.delete()


@task
def notify_new_reuse(reuse):
    for dataset in reuse.datasets:
        if dataset.organization:
            recipients = [m.user for m in dataset.organization.members]
        elif dataset.owner:
            recipients = dataset.owner
        else:
            recipients = None
        if recipients:
            mail.send(_('New reuse'), recipients, 'new_reuse', reuse=reuse,
                      dataset=dataset)
