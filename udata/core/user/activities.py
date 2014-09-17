# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.security import current_user

from udata.i18n import lazy_gettext as _
from udata.models import db, User, Dataset, Reuse, Organization, Activity
from udata.core.activity.tasks import write_activity
from udata.core.followers.signals import on_follow

from udata.core.dataset.activities import DatasetRelatedActivity
from udata.core.reuse.activities import ReuseRelatedActivity
from udata.core.organization.activities import OrgRelatedActivity


__all__ = (
    'UserFollowedDataset', 'UserFollowedReuse', 'UserFollowedOrganization', 'UserFollowedUser',
)


class FollowActivity(object):
    icon = 'fa fa-eye'
    badge_type = 'warning'


class UserStarredOrganization(FollowActivity, OrgRelatedActivity, Activity):
    key = 'organization:followed'
    label = _('followed an organization')


class UserFollowedUser(FollowActivity, Activity):
    key = 'user:followed'
    label = _('followed a user')
    related_to = db.ReferenceField(User)
    template = 'activity/user.html'


class UserFollowedDataset(FollowActivity, DatasetRelatedActivity, Activity):
    key = 'dataset:followed'
    label = _('followed a dataset')


class UserFollowedReuse(FollowActivity, ReuseRelatedActivity, Activity):
    key = 'reuse:followed'
    label = _('followed a reuse')


class UserFollowedOrganization(FollowActivity, OrgRelatedActivity, Activity):
    key = 'organization:followed'
    label = _('followed an organization')


@on_follow.connect
def write_activity_on_follow(follow, **kwargs):
    if isinstance(follow.following, Dataset):
        write_activity.delay(UserFollowedDataset, current_user._get_current_object(), follow.following)
    elif isinstance(follow.following, Reuse):
        write_activity.delay(UserFollowedReuse, current_user._get_current_object(), follow.following)
    elif isinstance(follow.following, Organization):
        write_activity.delay(UserFollowedOrganization, current_user._get_current_object(), follow.following)
    elif isinstance(follow.following, User):
        write_activity.delay(UserFollowedUser, current_user._get_current_object(), follow.following)
