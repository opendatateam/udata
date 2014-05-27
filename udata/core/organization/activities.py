# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.security import current_user

from udata.models import db, Organization, Activity
from udata.core.activity.tasks import write_activity


__all__ = ('UserCreatedOrganization', 'UserUpdatedOrganization')


class UserCreatedOrganization(Activity):
    organization = db.ReferenceField('Organization')


class UserUpdatedOrganization(Activity):
    organization = db.ReferenceField('Organization')


# class UserDeletedOrganization(Activity):
#     organization = db.ReferenceField('Organization')


@Organization.on_create.connect
def on_user_created_organization(organization):
    user = current_user._get_current_object()
    write_activity.delay(UserCreatedOrganization, user, organization, organization=organization)


@Organization.on_update.connect
def on_user_updated_organization(organization):
    user = current_user._get_current_object()
    write_activity.delay(UserUpdatedOrganization, user, organization, organization=organization)


# @Organization.on_delete.connect
# def on_user_deleted_organization(organization):
#     user = current_user._get_current_object()
#     organization = organization.organization
#     write_activity.delay(UserDeletedOrganization, user, organization, organization=organization)
