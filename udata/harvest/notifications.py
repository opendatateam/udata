# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.features.notifications.actions import notifier

from .models import HarvestSource, VALIDATION_PENDING

import logging

log = logging.getLogger(__name__)


@notifier('validate_harvester')
def validate_harvester_notifications(user):
    '''Notify admins about pending harvester validation'''
    if not user.sysadmin:
        return []

    notifications = []

    # Only fetch required fields for notification serialization
    # Greatly improve performances and memory usage
    qs = HarvestSource.objects(validation__state=VALIDATION_PENDING)
    qs = qs.only('id', 'created_at', 'name')

    for source in qs:
        notifications.append((source.created_at, {
            'id': source.id,
            'name': source.name,
        }))

    return notifications
