# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.metrics import Metric, MetricMetaClass
from udata.i18n import lazy_gettext as _
from udata.models import Follow

from .signals import on_follow, on_unfollow

__all__ = ('FollowersMetric', )


class FollowersMetricMetaclass(MetricMetaClass):
    def __new__(cls, name, bases, attrs):
        # Ensure any child class compute itself on follow/unfollow
        new_class = super(FollowersMetricMetaclass, cls).__new__(
            cls, name, bases, attrs)
        if new_class.model:
            def callback(follow):
                if isinstance(follow.following, new_class.model):
                    new_class(follow.following).trigger_update()
            on_follow.connect(callback, weak=False)
            on_unfollow.connect(callback, weak=False)
        return new_class


class FollowersMetric(Metric):
    name = 'followers'
    display_name = _('Followers')

    __metaclass__ = FollowersMetricMetaclass

    def get_value(self):
        return Follow.objects.followers(self.target).count()
