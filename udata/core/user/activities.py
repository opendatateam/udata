# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.security import current_user

from udata.models import db, Dataset, Reuse, Organization, Activity, Follow, FollowOrg, FollowDataset, FollowReuse
from udata.core.activity.tasks import write_activity
from udata.core.followers.signals import on_follow, on_unfollow


__all__ = (
    'UserStarredDataset', 'UserStarredReuse', 'UserStarredOrganization',
    'UserFollowedDataset', 'UserFollowedReuse', 'UserFollowedOrganization', 'UserFollowedUser',
)


class UserStarredDataset(Activity):
    dataset = db.ReferenceField('Dataset')


class UserStarredReuse(Activity):
    reuse = db.ReferenceField('Reuse')


class UserStarredOrganization(Activity):
    organization = db.ReferenceField('Organization')


class UserFollowedUser(Activity):
    followee = db.ReferenceField('User')


class UserFollowedDataset(Activity):
    followee = db.ReferenceField('Dataset')


class UserFollowedReuse(Activity):
    followee = db.ReferenceField('Reuse')


class UserFollowedOrganization(Activity):
    followee = db.ReferenceField('Organization')


@Follow.on_new.connect
def on_user_follow(document, **kwargs):
    if isinstance(document, FollowDataset):
        write_activity.delay(UserFollowedDataset, current_user._get_current_object(), followee=document.following)
    elif isinstance(document, FollowReuse):
        write_activity.delay(UserFollowedReuse, current_user._get_current_object(), followee=document.following)
    elif isinstance(document, FollowOrg):
        write_activity.delay(UserFollowedOrganization, current_user._get_current_object(), followee=document.following)
    else:
        write_activity.delay(UserFollowedUser, current_user._get_current_object(), followee=document.following)


@Dataset.on_star.connect
def on_user_starred_dataset(dataset):
    write_activity.delay(UserStarredDataset, current_user._get_current_object(), dataset=dataset)


@Reuse.on_star.connect
def on_user_starred_reuse(reuse):
    write_activity.delay(UserStarredReuse, current_user._get_current_object(), reuse=reuse)


@Organization.on_star.connect
def on_user_starred_org(organization):
    write_activity.delay(UserStarredOrganization, current_user._get_current_object(), organization=organization)
