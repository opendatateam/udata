# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _

from udata.core.followers.metrics import FollowersMetric

from udata.core.issues.metrics import IssuesMetric
from udata.core.discussions.metrics import DiscussionsMetric

from .models import Reuse

__all__ = (
    'DatasetsMetric', 'ReuseFollowers', 'ReuseIssuesMetric',
    'ReuseDiscussionsMetric'
)


class DatasetsMetric(Metric):
    model = Reuse
    name = 'datasets'
    display_name = _('Datasets')

    def get_value(self):
        return len(self.target.datasets)

DatasetsMetric.connect(Reuse.on_create, Reuse.on_update)


class ReuseFollowers(FollowersMetric):
    model = Reuse


class ReuseIssuesMetric(IssuesMetric):
    model = Reuse


class ReuseDiscussionsMetric(DiscussionsMetric):
    model = Reuse
