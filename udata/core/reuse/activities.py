# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask_security import current_user

from udata.i18n import lazy_gettext as _
from udata.models import db, Reuse, Activity
from udata.core.activity.tasks import write_activity


__all__ = (
    'UserCreatedReuse', 'UserUpdatedReuse', 'UserDeletedReuse',
    'ReuseRelatedActivity'
)


class ReuseRelatedActivity(object):
    template = 'activity/reuse.html'
    related_to = db.ReferenceField('Reuse')


class UserCreatedReuse(ReuseRelatedActivity, Activity):
    key = 'reuse:created'
    icon = 'fa fa-plus'
    badge_type = 'success'
    label = _('created a reuse')


class UserUpdatedReuse(ReuseRelatedActivity, Activity):
    key = 'reuse:updated'
    icon = 'fa fa-pencil'
    label = _('updated a reuse')


class UserDeletedReuse(ReuseRelatedActivity, Activity):
    key = 'reuse:deleted'
    icon = 'fa fa-remove'
    badge_type = 'error'
    label = _('deleted a reuse')


@Reuse.on_create.connect
def on_user_created_reuse(reuse):
    if not reuse.private and current_user and current_user.is_authenticated:
        user = current_user._get_current_object()
        organization = reuse.organization
        write_activity.delay(UserCreatedReuse, user, reuse, organization)


@Reuse.on_update.connect
def on_user_updated_reuse(reuse):
    if not reuse.private and current_user and current_user.is_authenticated:
        user = current_user._get_current_object()
        organization = reuse.organization
        write_activity.delay(UserUpdatedReuse, user, reuse, organization)


@Reuse.on_delete.connect
def on_user_deleted_reuse(reuse):
    if not reuse.private and current_user and current_user.is_authenticated:
        user = current_user._get_current_object()
        organization = reuse.organization
        write_activity.delay(UserDeletedReuse, user, reuse, organization)
