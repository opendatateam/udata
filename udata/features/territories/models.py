# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import License, Organization

__all__ = (
    'TerritoryDataset', 'ResourceBasedTerritoryDataset', 'TERRITORY_DATASETS'
)


TERRITORY_DATASETS = {
    'commune': {},
    'departement': {},
    'region': {},
    'country': {}
}


class TerritoryDataset(object):
    order = 0
    id = ''
    title = ''
    organization_id = ''
    url_template = ''
    description = ''
    license_id = 'fr-lo'

    def __init__(self, territory):
        self.territory = territory

    @property
    def url(self):
        return self.url_template.format(code=self.territory.code)

    @property
    def slug(self):
        return '{territory_id}:{id}'.format(
            territory_id=self.territory.id, id=self.id)

    @property
    def organization(self):
        return Organization.objects.get(id=self.organization_id)

    @property
    def license(self):
        return License.objects(id=self.license_id).first()


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
