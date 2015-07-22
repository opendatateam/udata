# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse, User, Follow

from udata.core.followers.metrics import FollowersMetric
from udata.core.followers.signals import on_follow, on_unfollow


__all__ = (
    'DatasetsMetric', 'ReusesMetric', 'UserFollowersMetric',
    'UserFollowingMetric'
)


class UserMetric(Metric):
    model = User

    @property
    def user(self):
        return self.target


class DatasetsMetric(UserMetric):
    name = 'datasets'
    display_name = _('Datasets')

    def get_value(self):
        return Dataset.objects(owner=self.user).visible().count()


@Dataset.on_create.connect
@Dataset.on_update.connect
def update_datasets_metrics(document, **kwargs):
    DatasetsMetric(document.owner).trigger_update()


class ReusesMetric(UserMetric):
    name = 'reuses'
    display_name = _('Reuses')

    def get_value(self):
        return Reuse.objects(owner=self.user).count()

ReusesMetric.connect(Reuse.on_create, Reuse.on_update)


class UserFollowersMetric(FollowersMetric):
    model = User


class UserFollowingMetric(UserMetric):
    name = 'following'
    display_name = _('Following')

    def get_value(self):
        return Follow.objects.following(self.user).count()


@on_follow.connect
@on_unfollow.connect
def update_user_following_metric(follow):
    UserFollowingMetric(follow.follower).trigger_update()
