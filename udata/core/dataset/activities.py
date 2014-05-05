# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.security import current_user

from udata.models import db, Dataset, Activity
from udata.core.activity.tasks import write_activity


__all__ = ('UserCreatedDataset', 'UserUpdatedDataset', 'UserDeletedDataset')


class UserCreatedDataset(Activity):
    dataset = db.ReferenceField('Dataset')


class UserUpdatedDataset(Activity):
    dataset = db.ReferenceField('Dataset')


class UserDeletedDataset(Activity):
    dataset = db.ReferenceField('Dataset')


@Dataset.on_create.connect
def on_user_created_dataset(dataset):
    user = current_user._get_current_object()
    organization = dataset.organization
    write_activity.delay(UserCreatedDataset, user, organization, dataset=dataset)


@Dataset.on_update.connect
def on_user_updated_dataset(dataset):
    user = current_user._get_current_object()
    organization = dataset.organization
    write_activity.delay(UserUpdatedDataset, user, organization, dataset=dataset)


@Dataset.on_delete.connect
def on_user_deleted_dataset(dataset):
    user = current_user._get_current_object()
    organization = dataset.organization
    write_activity.delay(UserDeletedDataset, user, organization, dataset=dataset)
