from flask_security import current_user

from udata.i18n import lazy_gettext as _
from udata.models import db, User, Dataset, Reuse, Organization, Activity
from udata.core.followers.signals import on_follow
from udata.core.discussions.signals import (
    on_new_discussion, on_new_discussion_comment
)
from udata.core.dataset.activities import DatasetRelatedActivity
from udata.core.reuse.activities import ReuseRelatedActivity
from udata.core.organization.activities import OrgRelatedActivity


__all__ = (
    'UserFollowedDataset', 'UserFollowedReuse', 'UserFollowedOrganization',
    'UserFollowedUser', 'UserDiscussedDataset', 'UserDiscussedReuse'
)


class FollowActivity(object):
    icon = 'fa fa-eye'
    badge_type = 'warning'


class DiscussActivity(object):
    icon = 'fa fa-comments'
    badge_type = 'warning'


class UserStarredOrganization(FollowActivity, OrgRelatedActivity, Activity):
    key = 'organization:followed'
    label = _('followed an organization')


class UserFollowedUser(FollowActivity, Activity):
    key = 'user:followed'
    label = _('followed a user')
    related_to = db.ReferenceField(User)
    template = 'activity/user.html'


class UserDiscussedDataset(DiscussActivity, DatasetRelatedActivity, Activity):
    key = 'dataset:discussed'
    label = _('discussed a dataset')


class UserDiscussedReuse(DiscussActivity, ReuseRelatedActivity, Activity):
    key = 'reuse:discussed'
    label = _('discussed a reuse')


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
    if current_user.is_authenticated:
        if isinstance(follow.following, Dataset):
            UserFollowedDataset.emit(follow.following)
        elif isinstance(follow.following, Reuse):
            UserFollowedReuse.emit(follow.following)
        elif isinstance(follow.following, Organization):
            UserFollowedOrganization.emit(follow.following)
        elif isinstance(follow.following, User):
            UserFollowedUser.emit(follow.following)


@on_new_discussion.connect
@on_new_discussion_comment.connect
def write_activity_on_discuss(discussion, **kwargs):
    if current_user.is_authenticated:
        if isinstance(discussion.subject, Dataset):
            UserDiscussedDataset.emit(discussion.subject)
        elif isinstance(discussion.subject, Reuse):
            UserDiscussedReuse.emit(discussion.subject)
