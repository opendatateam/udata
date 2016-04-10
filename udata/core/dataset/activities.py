# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.auth import current_user
from udata.i18n import lazy_gettext as _
from udata.models import db, Dataset, Activity
from udata.core.activity.tasks import write_activity


__all__ = (
    'UserCreatedDataset', 'UserUpdatedDataset', 'UserDeletedDataset',
    'DatasetRelatedActivity'
)


class DatasetRelatedActivity(object):
    template = 'activity/dataset.html'
    related_to = db.ReferenceField('Dataset')


class UserCreatedDataset(DatasetRelatedActivity, Activity):
    key = 'dataset:created'
    icon = 'fa fa-plus'
    badge_type = 'success'
    label = _('created a dataset')


class UserUpdatedDataset(DatasetRelatedActivity, Activity):
    key = 'dataset:updated'
    icon = 'fa fa-pencil'
    label = _('updated a dataset')


class UserDeletedDataset(DatasetRelatedActivity, Activity):
    key = 'dataset:deleted'
    icon = 'fa fa-remove'
    badge_type = 'error'
    label = _('deleted a dataset')


@Dataset.on_create.connect
def on_user_created_dataset(dataset):
    if (not dataset.private and current_user and
            current_user.is_authenticated):
        user = current_user._get_current_object()
        organization = dataset.organization
        write_activity.delay(UserCreatedDataset, user, dataset, organization)


@Dataset.on_update.connect
def on_user_updated_dataset(dataset):
    if (not dataset.private and current_user and
            current_user.is_authenticated):
        user = current_user._get_current_object()
        organization = dataset.organization
        write_activity.delay(UserUpdatedDataset, user, dataset, organization)


@Dataset.on_delete.connect
def on_user_deleted_dataset(dataset):
    if (not dataset.private and current_user and
            current_user.is_authenticated):
        user = current_user._get_current_object()
        organization = dataset.organization
        write_activity.delay(UserDeletedDataset, user, dataset, organization)
