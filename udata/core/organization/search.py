# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Organization
from udata.search import ModelSearchAdapter, Sort, RangeFilter, i18n_analyzer

__all__ = ('OrganizationSearch', )


class OrganizationSearch(ModelSearchAdapter):
    model = Organization
    fields = (
        'name^2',
        'description',
    )
    sorts = {
        'name': Sort('name.raw'),
        'reuses': Sort('nb_reuses'),
        'datasets': Sort('nb_datasets'),
        'stars': Sort('nb_stars'),
    }
    filters = {
        'reuses': RangeFilter('nb_reuses'),
        'datasets': RangeFilter('nb_datasets'),
    }
    mapping = {
        'properties': {
            'name': {
                'type': 'string',
                'fields': {
                    'raw': {'type': 'string', 'index': 'not_analyzed'}
                }
            },
            'description': {'type': 'string', 'analyzer': i18n_analyzer},
            'url': {'type': 'string'},
            'nb_datasets': {'type': 'integer'},
            'nb_reuses': {'type': 'integer'},
        }
    }

    @classmethod
    def serialize(cls, organization):
        return {
            'name': organization.name,
            'description': organization.description,
            'url': organization.url,
            'nb_datasets': organization.metrics.get('datasets', 0),
            'nb_reuses': organization.metrics.get('reuses', 0),
            'nb_stars': organization.metrics.get('stars', 0),
        }
