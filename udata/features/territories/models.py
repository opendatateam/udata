# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Organization

__all__ = ('TerritoryDataset', 'ResourceBasedTerritoryDataset')


class TerritoryDataset(object):
    id = ''
    title = ''
    organization_id = ''
    url_template = ''
    description = ''

    def __init__(self, territory):
        self.territory = territory

    @property
    def url(self):
        return self.url_template.format(code=self.territory.code)

    @property
    def slug(self):
        return '{territory_id}-{id}'.format(
            territory_id=self.territory.id.replace('/', '-'), id=self.id)

    @property
    def organization(self):
        return Organization.objects.get(id=self.organization_id)


class ResourceBasedTerritoryDataset(TerritoryDataset):
    dataset_id = ''
    resource_id = ''
    territory_attr = ''
    csv_column = ''

    def url_for(self, external=False):
        return url_for('territories.territory_dataset_resource',
                       territory=self.territory,
                       dataset=self.dataset_id,
                       resource_id=self.resource_id,
                       territory_attr=self.territory_attr,
                       csv_column=self.csv_column,
                       _external=external)
    url = property(url_for)

    @property
    def external_url(self):
        return self.url_for(external=True)
