# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask_security import current_user

from udata.i18n import lazy_gettext as _
from udata.models import db, Organization, Activity
from udata.core.activity.tasks import write_activity


__all__ = (
    'UserCreatedOrganization', 'UserUpdatedOrganization', 'OrgRelatedActivity'
)


class OrgRelatedActivity(object):
    related_to = db.ReferenceField('Organization')
    template = 'activity/organization.html'


class UserCreatedOrganization(OrgRelatedActivity, Activity):
    key = 'organization:created'
    icon = 'fa fa-plus'
    badge_type = 'success'
    label = _('created an organization')


class UserUpdatedOrganization(OrgRelatedActivity, Activity):
    key = 'organization:updated'
    icon = 'fa fa-pencil'
    badge_type = 'error'
    label = _('updated an organization')


@Organization.on_create.connect
def on_user_created_organization(organization):
    if current_user and current_user.is_authenticated:
        user = current_user._get_current_object()
        write_activity.delay(
            UserCreatedOrganization, user, organization,
            organization=organization)


@Organization.on_update.connect
def on_user_updated_organization(organization):
    if current_user and current_user.is_authenticated:
        user = current_user._get_current_object()
        write_activity.delay(
            UserUpdatedOrganization, user, organization,
            organization=organization)
