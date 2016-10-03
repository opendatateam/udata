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

    # Only fetch required attributes
    qs = issues_for(user).only('id', 'title', 'created', 'subject')

    # Do not dereference subject (so it's a DBRef)
    for issue in qs.no_dereference():
        notifications.append((issue.created, {
            'id': issue.id,
            'title': issue.title,
            'subject': {
                'id': issue.subject['_ref'].id,
                'type': issue.subject['_cls'].lower(),
            }
        }))

    return notifications
