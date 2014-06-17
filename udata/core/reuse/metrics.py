# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.models import Reuse

from udata.core.followers.models import FollowReuse
from udata.core.followers.metrics import FollowersMetric


__all__ = ('DatasetsMetric', )


class DatasetsMetric(Metric):
    model = Reuse
    name = 'datasets'
    display_name = _('Datasets')

    def get_value(self):
        return len(self.target.datasets)

DatasetsMetric.connect(Reuse.on_create, Reuse.on_update)


class ReuseFollowers(FollowersMetric):
    model = Reuse


@FollowReuse.on_new.connect
def on_new_reuse_follower(follow):
    ReuseFollowers(follow.following).trigger_update()
