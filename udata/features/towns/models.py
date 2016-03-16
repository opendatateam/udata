# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Organization

__all__ = ('TownDataset', 'ResourceBasedTownDataset')


class TownDataset(object):
    id = ''
    title = ''
    organization_id = ''
    url_template = ''
    description = ''

    def __init__(self, town):
        self.town = town

    @property
    def url(self):
        return self.url_template.format(code=self.town.code)

    @property
    def slug(self):
        return '{town_id}-{id}'.format(
            town_id=self.town.id.replace('/', '-'), id=self.id)

    @property
    def organization(self):
        return Organization.objects.get(id=self.organization_id)


class ResourceBasedTownDataset(TownDataset):
    dataset_id = ''
    resource_id = ''
    town_attr = ''
    csv_column = ''

    def url_for(self, external=False):
        return url_for('towns.town_dataset_resource',
                       town=self.town,
                       dataset=self.dataset_id,
                       resource_id=self.resource_id,
                       town_attr=self.town_attr,
                       csv_column=self.csv_column,
                       _external=external)
    url = property(url_for)

    @property
    def external_url(self):
        return self.url_for(external=True)
