# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse, User


__all__ = ('DatasetReuses', 'DatasetStars')


class DatasetReuses(Metric):
    model = Dataset
    name = 'reuses'
    display_name = _('Reuses')

    def get_value(self):
        return Reuse.objects(datasets=self.target).count()


class DatasetStars(Metric):
    model = Dataset
    name = 'stars'
    display_name = _('Stars')

    def get_value(self):
        return User.objects(starred_datasets=self.target).count()


DatasetStars.connect(Dataset.on_star, Dataset.on_unstar)


@Reuse.on_update.connect
@Reuse.on_create.connect
def update_dataset_reuses_metric(reuse, **kwargs):
    for dataset in reuse.datasets:
        metric = DatasetReuses(dataset)
        metric.trigger_update()

