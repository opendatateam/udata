# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from . import SiteMetric
from udata.i18n import lazy_gettext as _
from udata.models import Dataset, Reuse, User, Organization, Resource, Follow


__all__ = ('DatasetsMetric', 'ReusesMetric', 'ResourcesMetric', 'UsersMetric', 'OrganizationsMetric', 'StarsMetric')


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
        return Reuse.objects.count()

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
        return Organization.objects.count()

OrganizationsMetric.connect(Organization.on_update)


class FollowersMetric(SiteMetric):
    name = 'followers'
    display_name = _('Followers')

    def get_value(self):
        return Follow.objects(until=None).count()

FollowersMetric.connect(Follow.on_new)
