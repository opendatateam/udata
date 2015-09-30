# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.models import Transfer
from udata.features.notifications.actions import notifier


import logging

log = logging.getLogger(__name__)


@notifier('transfer_request')
def transfer_request_notifications(user):
    '''Notify user about pending transfer requests'''
    orgs = [o for o in user.organizations if o.is_member(user)]
    notifications = []

    for transfer in Transfer.objects(
            recipient__in=[user] + orgs, status='pending'):
        notifications.append((transfer.created, {
            'id': transfer.id,
            'subject': {
                'class': transfer.subject.__class__.__name__.lower(),
                'id': transfer.subject.id
            }
        }))

    return notifications
