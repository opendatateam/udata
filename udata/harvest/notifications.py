# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.features.notifications.actions import notifier

from .models import HarvestSource

import logging

log = logging.getLogger(__name__)


@notifier('validate_harvester')
def validate_harvester_notifications(user):
    '''Notify admins about pending harvester validation'''
    if not user.sysadmin:
        return []

    notifications = []

    for source in HarvestSource.objects(validated=False):
        notifications.append((source.created_at, {
            'id': source.id,
            'name': source.name,
        }))

    return notifications
