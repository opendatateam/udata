# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.metrics import Metric
from udata.i18n import lazy_gettext as _
from udata.core.followers.metrics import FollowersMetric
from udata.models import db, Dataset, Reuse, Organization

__all__ = (
    'DatasetsMetric', 'ReusesMetric', 'MembersMetric', 'OrgFollowersMetric',
)


class DatasetsMetric(Metric):
    model = Organization
    name = 'datasets'
    display_name = _('Datasets')

    def get_value(self):
        org = self.target
        return Dataset.objects(organization=org).visible().count()


@Dataset.on_create.connect
@Dataset.on_update.connect
def update_datasets_metrics(document, **kwargs):
    if document.organization:
        DatasetsMetric(document.organization).trigger_update()


class ReusesMetric(Metric):
    model = Organization
    name = 'reuses'
    display_name = _('Reuses')

    def get_value(self):
        return Reuse.objects(organization=self.target).count()


@Reuse.on_create.connect
@Reuse.on_update.connect
def update_reuses_metrics(document, **kwargs):
    if document.organization:
        ReusesMetric(document.organization).trigger_update()


class PermitedReusesMetric(Metric):
    model = Organization
    name = 'permitted_reuses'
    display_name = _('Permitted reuses')

    def get_value(self):
        ids = [d.id
               for d in Dataset.objects(organization=self.target).only('id')]
        return Reuse.objects(datasets__in=ids).count()


class MembersMetric(Metric):
    model = Organization
    name = 'members'
    display_name = _('Members')

    def get_value(self):
        return len(self.target.members)


MembersMetric.connect(Organization.on_create, Organization.on_update)


class OrgFollowersMetric(FollowersMetric):
    model = Organization


@db.Owned.on_owner_change.connect
def update_downer_metrics(document, previous):
    if not isinstance(previous, Organization):
        return
    if isinstance(document, Dataset):
        DatasetsMetric(previous).trigger_update()
    elif isinstance(document, Reuse):
        ReusesMetric(previous).trigger_update()
