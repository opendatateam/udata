# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.features.notifications.actions import notifier

from .actions import issues_for


import logging

log = logging.getLogger(__name__)


@notifier('issue')
def issues_notifications(user):
    '''Notify user about open issues'''
    notifications = []

    for issue in issues_for(user):
        notifications.append((issue.created, {
            'id': issue.id,
            'title': issue.title,
            'subject': {
                'id': issue.subject.id,
                'type': issue.subject.__class__.__name__.lower(),
            }
        }))

    return notifications
