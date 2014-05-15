# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.models import db, Dataset, Reuse, User, Organization, Follow


__all__ = ('DatasetsMetric', 'ReusesMetric', 'FollowersMetric', 'StarsMetric')


class UserMetric(Metric):
    model = User

    @property
    def user(self):
        self.target


class DatasetsMetric(UserMetric):
    name = 'datasets'
    display_name = _('Datasets')

    def get_value(self):
        return Dataset.objects(owner=self.target).visible().count()


@Dataset.on_create.connect
@Dataset.on_update.connect
def update_datasets_metrics(document, **kwargs):
    DatasetsMetric(document.owner).trigger_update()


class ReusesMetric(UserMetric):
    name = 'reuses'
    display_name = _('Reuses')

    def get_value(self):
        return Reuse.objects(owner=self.target).count()

ReusesMetric.connect(Reuse.on_create, Reuse.on_update)


class FollowersMetric(UserMetric):
    name = 'followers'
    display_name = _('Followers')

    def get_value(self):
        return Follow.objects.followers(self.user).count()


class FollowingMetric(UserMetric):
    name = 'following'
    display_name = _('Following')

    def get_value(self):
        return Follow.objects.following(self.user).count()


@Follow.on_new.connect
def update_followers_metric(document, **kwargs):
    FollowingMetric(document.follower).trigger_update()
    if isinstance(document.following, User):
        FollowersMetric(document.following).trigger_update()
