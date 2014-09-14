# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import g

from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse, User, Organization, Resource, Follow
from udata.core.metrics import Metric
from udata.core.followers.signals import on_follow, on_unfollow

from .models import Site
from .views import current_site

__all__ = ('DatasetsMetric', 'ReusesMetric', 'ResourcesMetric', 'UsersMetric', 'OrganizationsMetric')


class SiteMetric(Metric):
    model = Site

    def __init__(self, value=None):
        super(SiteMetric, self).__init__(current_site.id, value)

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
                total += doc.resources.length;
            });
            return total;
        }
        '''))

ResourcesMetric.connect(Resource.on_added, Resource.on_deleted)


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


class FollowersMetric(SiteMetric):
    name = 'followers'
    display_name = _('Followers')

    def get_value(self):
        return Follow.objects(until=None).count()

FollowersMetric.connect(on_follow, on_unfollow)
