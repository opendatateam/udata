# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.models import Reuse, Dataset, Issue
from udata.features.notifications.actions import notifier


import logging

log = logging.getLogger(__name__)


@notifier('issue')
def issues_notifications(user):
    '''Notify user about open issues'''
    orgs = [o for o in user.organizations if o.is_member(user)]
    datasets = Dataset.objects.owned_by(user, *orgs)
    reuses = Reuse.objects.owned_by(user, *orgs)
    notifications = []

    for issue in Issue.objects(
            subject__in=list(datasets) + list(reuses),
            closed__exists=False):
        notifications.append((issue.created, {
            'id': issue.id,
            'title': issue.title,
            'subject': {
                'id': issue.subject.id,
                'type': issue.subject.__class__.__name__.lower(),
            }
        }))

    return notifications
