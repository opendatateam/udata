# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.models import db, Dataset, Reuse, User, Organization


__all__ = ('DatasetsMetric', 'ReusesMetric', 'MembersMetric', 'StarsMetric')


class DatasetsMetric(Metric):
    model = Organization
    name = 'datasets'
    display_name = _('Datasets')

    def get_value(self):
        org = self.target
        return Dataset.objects(db.Q(organization=org) | db.Q(supplier=org)).visible().count()


@Dataset.on_create.connect
@Dataset.on_update.connect
def update_datasets_metrics(document, **kwargs):
    DatasetsMetric(document.organization).trigger_update()
    DatasetsMetric(document.supplier).trigger_update()


class ReusesMetric(Metric):
    model = Reuse
    name = 'reuses'
    display_name = _('Reuses')

    def get_value(self):
        return Reuse.objects(organization=self.target).count()

ReusesMetric.connect(Reuse.on_create, Reuse.on_update)


class MembersMetric(Metric):
    model = Organization
    name = 'members'
    display_name = _('Members')

    def get_value(self):
        return len(self.target.members)

MembersMetric.connect(Organization.on_create, Organization.on_update)


class StarsMetric(Metric):
    model = Organization
    name = 'stars'
    display_name = _('Stars')

    def get_value(self):
        return User.objects(starred_organizations=self.target).count()


StarsMetric.connect(Organization.on_star, Organization.on_unstar)
