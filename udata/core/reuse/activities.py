# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.security import current_user

from udata.models import db, Reuse, Activity
from udata.core.activity.tasks import write_activity


__all__ = ('UserCreatedReuse', 'UserUpdatedReuse', 'UserDeletedReuse')


class UserCreatedReuse(Activity):
    reuse = db.ReferenceField('Reuse')


class UserUpdatedReuse(Activity):
    reuse = db.ReferenceField('Reuse')


class UserDeletedReuse(Activity):
    reuse = db.ReferenceField('Reuse')


@Reuse.on_create.connect
def on_user_created_reuse(reuse):
    user = current_user._get_current_object()
    organization = reuse.organization
    write_activity.delay(UserCreatedReuse, user, organization, reuse=reuse)


@Reuse.on_update.connect
def on_user_updated_reuse(reuse):
    user = current_user._get_current_object()
    organization = reuse.organization
    write_activity.delay(UserUpdatedReuse, user, organization, reuse=reuse)


@Reuse.on_delete.connect
def on_user_deleted_reuse(reuse):
    user = current_user._get_current_object()
    organization = reuse.organization
    write_activity.delay(UserDeletedReuse, user, organization, reuse=reuse)
