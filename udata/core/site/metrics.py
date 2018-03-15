# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse, User, Organization, Resource, Follow
from udata.core.metrics import Metric
from udata.core.followers.signals import on_follow, on_unfollow

from .models import Site
from .views import current_site

__all__ = (
    'DatasetsMetric', 'ReusesMetric', 'ResourcesMetric', 'UsersMetric',
    'OrganizationsMetric'
)


class SiteMetric(Metric):
    model = Site

    def __init__(self, value=None):
        if current_site is None:
            raise ValueError('Need to be inside app context')
        super(SiteMetric, self).__init__(current_site._get_current_object(),
                                         value)

    @classmethod
    def update(cls):
        metric = cls()
        metric.trigger_update()

    @classmethod
    def connect(cls, *signals):
        def callback(sender, **kwargs):
            cls.update()
        for signal in signals:
            signal.connect(callback, weak=False)


class DatasetsMetric(SiteMetric):
    name = 'datasets'
    display_name = _('Datasets')

    def get_value(self):
        return Dataset.objects.visible().count()


DatasetsMetric.connect(Dataset.on_create, Dataset.on_update)


class ReusesMetric(SiteMetric):
    name = 'reuses'
    display_name = _('Reuses')

    def get_value(self):
        return Reuse.objects.visible().count()

ReusesMetric.connect(Reuse.on_create, Reuse.on_update)


class ResourcesMetric(SiteMetric):
    name = 'resources'
    display_name = _('Resources')

    def get_value(self):
        return int(Dataset.objects.visible().exec_js('''
        function() {
            var total = 0
            db[collection].find(query).forEach(function(doc) {
                if (doc.resources && doc.resources.length) {
                    total += doc.resources.length;
                }
            });
            return total;
        }
        '''))

ResourcesMetric.connect(Dataset.on_create, Dataset.on_update,
                        Resource.on_added, Resource.on_deleted)


class UsersMetric(SiteMetric):
    name = 'users'
    display_name = _('Users')

    def get_value(self):
        return User.objects.count()

UsersMetric.connect(User.on_update, User.on_create)


class OrganizationsMetric(SiteMetric):
    name = 'organizations'
    display_name = _('Organizations')

    def get_value(self):
        return Organization.objects.visible().count()

OrganizationsMetric.connect(Organization.on_update)


class SiteFollowersMetric(SiteMetric):
    name = 'followers'
    display_name = _('Followers')

    def get_value(self):
        return Follow.objects(until=None).count()

SiteFollowersMetric.connect(on_follow, on_unfollow)


class MaxDatasetFollowersMetric(SiteMetric):
    name = 'max_dataset_followers'
    display_name = _('Maximum dataset followers')
    archived = False

    def get_value(self):
        dataset = (Dataset.objects(metrics__followers__gt=0).visible()
                          .order_by('-metrics.followers').first())
        return dataset.metrics['followers'] if dataset else 0

MaxDatasetFollowersMetric.connect(Dataset.on_create, Dataset.on_update)


class MaxDatasetReusesMetric(SiteMetric):
    name = 'max_dataset_reuses'
    display_name = _('Maximum dataset reuses')
    archived = False

    def get_value(self):
        dataset = (Dataset.objects(metrics__reuses__gt=0).visible()
                   .order_by('-metrics.reuses').first())
        return dataset.metrics['reuses'] if dataset else 0

MaxDatasetReusesMetric.connect(Dataset.on_create, Dataset.on_update)


class MaxReuseDatasetsMetric(SiteMetric):
    name = 'max_reuse_datasets'
    display_name = _('Maximum datasets in reuses')
    archived = False

    def get_value(self):
        reuse = (Reuse.objects(metrics__datasets__gt=0).visible()
                 .order_by('-metrics.datasets').first())
        return reuse.metrics['datasets'] if reuse else 0

MaxReuseDatasetsMetric.connect(Reuse.on_create, Reuse.on_update)


class MaxReuseFollowersMetric(SiteMetric):
    name = 'max_reuse_followers'
    display_name = _('Maximum reuse followers')
    archived = False

    def get_value(self):
        reuse = (Reuse.objects(metrics__followers__gt=0).visible()
                 .order_by('-metrics.followers').first())
        return reuse.metrics['followers'] if reuse else 0

MaxReuseFollowersMetric.connect(on_follow, on_unfollow)


class MaxOrgFollowersMetric(SiteMetric):
    name = 'max_org_followers'
    display_name = _('Maximum organization followers')
    archived = False

    def get_value(self):
        org = (Organization.objects(metrics__followers__gt=0).visible()
               .order_by('-metrics.followers').first())
        return org.metrics['followers'] if org else 0

MaxOrgFollowersMetric.connect(Organization.on_create, Organization.on_update,
                              on_follow, on_unfollow)


class MaxOrgReusesMetric(SiteMetric):
    name = 'max_org_reuses'
    display_name = _('Maximum organization reuses')
    archived = False

    def get_value(self):
        org = (Organization.objects(metrics__reuses__gt=0).visible()
               .order_by('-metrics.reuses').first())
        return org.metrics['reuses'] if org else 0


MaxOrgReusesMetric.connect(Dataset.on_create, Dataset.on_update)


class MaxOrgDatasetsMetric(SiteMetric):
    name = 'max_org_datasets'
    display_name = _('Maximum organization datasets')
    archived = False

    def get_value(self):
        org = (Organization.objects(metrics__datasets__gt=0).visible()
               .order_by('-metrics.datasets').first())
        return org.metrics['datasets'] if org else 0

MaxOrgDatasetsMetric.connect(Organization.on_create, Organization.on_update,
                             Reuse.on_create, Reuse.on_update)
