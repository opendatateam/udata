# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.models import Reuse, Dataset, Discussion
from udata.features.notifications.actions import notifier


import logging

log = logging.getLogger(__name__)


@notifier('discussion')
def discussions_notifications(user):
    '''Notify user about open discussions'''
    orgs = [o for o in user.organizations if o.is_member(user)]
    datasets = Dataset.objects.owned_by(user, *orgs)
    reuses = Reuse.objects.owned_by(user, *orgs)
    notifications = []

    for discussion in Discussion.objects(
            subject__in=list(datasets) + list(reuses),
            closed__exists=False):
        notifications.append((discussion.created, {
            'id': discussion.id,
            'title': discussion.title,
            'subject': {
                'id': discussion.subject.id,
                'type': discussion.subject.__class__.__name__.lower(),
            }
        }))

    return notifications
