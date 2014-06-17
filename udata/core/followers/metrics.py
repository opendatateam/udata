# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.models import User, Dataset, Organization
from udata.models import Follow, Follow, FollowOrg, FollowDataset


# __all__ = ('UserFollowers', 'UserFollowing')


class FollowersMetric(Metric):
    name = 'followers'
    display_name = _('Followers')

    def get_value(self):
        return Follow.objects.followers(self.target).count()


# class UserFollowers(FollowersMetric):
#     model = User


class OrgFollowers(FollowersMetric):
    model = Organization


class DatasetFollowers(FollowersMetric):
    model = Dataset


@FollowOrg.on_new.connect
def on_new_org_follower(follow):
    OrgFollowers(follow.following).trigger_update()


@FollowDataset.on_new.connect
def on_new_dataset_follower(follow):
    DatasetFollowers(follow.following).trigger_update()
