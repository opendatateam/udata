# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.core.followers.metrics import FollowersMetric
from udata.models import db, Dataset, Reuse, User, Organization, FollowOrg


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
    model = Organization
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


class OrgFollowersMetric(FollowersMetric):
    model = Organization


@FollowOrg.on_new.connect
def update_followers_metric(document, **kwargs):
    OrgFollowersMetric(document.following).trigger_update()
