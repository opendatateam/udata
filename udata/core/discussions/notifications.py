# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.features.notifications.actions import notifier

from .actions import discussions_for


import logging

log = logging.getLogger(__name__)


@notifier('discussion')
def discussions_notifications(user):
    '''Notify user about open discussions'''
    notifications = []

    for discussion in discussions_for(user):
        notifications.append((discussion.created, {
            'id': discussion.id,
            'title': discussion.title,
            'subject': {
                'id': discussion.subject.id,
                'type': discussion.subject.__class__.__name__.lower(),
            }
        }))

    return notifications
