# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.security import current_user

from udata.models import db, Dataset, Reuse, Organization, Activity
from udata.core.activity.tasks import write_activity


__all__ = ('UserStarredDataset', 'UserStarredReuse', 'UserStarredOrganization')


class UserStarredDataset(Activity):
    dataset = db.ReferenceField('Dataset')


class UserStarredReuse(Activity):
    reuse = db.ReferenceField('Reuse')


class UserStarredOrganization(Activity):
    organization = db.ReferenceField('Organization')


@Dataset.on_star.connect
def on_user_starred_dataset(dataset):
    write_activity.delay(UserStarredDataset, current_user._get_current_object(), dataset=dataset)


@Reuse.on_star.connect
def on_user_starred_reuse(reuse):
    write_activity.delay(UserStarredReuse, current_user._get_current_object(), reuse=reuse)


@Organization.on_star.connect
def on_user_starred_org(organization):
    write_activity.delay(UserStarredOrganization, current_user._get_current_object(), organization=organization)
