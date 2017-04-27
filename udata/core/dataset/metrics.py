# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse

from udata.core.issues.metrics import IssuesMetric
from udata.core.discussions.metrics import DiscussionsMetric
from udata.core.followers.metrics import FollowersMetric


__all__ = (
    'DatasetReuses', 'DatasetIssuesMetric', 'DatasetFollowers',
    'DatasetDiscussionsMetric'
)


class DatasetReuses(Metric):
    model = Dataset
    name = 'reuses'
    display_name = _('Reuses')

    def get_value(self):
        return Reuse.objects(datasets=self.target).visible().count()


@Reuse.on_update.connect
@Reuse.on_create.connect
def update_dataset_reuses_metric(reuse, **kwargs):
    for dataset in reuse.datasets:
        metric = DatasetReuses(dataset)
        metric.trigger_update()


class DatasetIssuesMetric(IssuesMetric):
    model = Dataset


class DatasetDiscussionsMetric(DiscussionsMetric):
    model = Dataset


class DatasetFollowers(FollowersMetric):
    model = Dataset
