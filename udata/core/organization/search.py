# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Organization
from udata.search import ModelSearchAdapter, Sort, RangeFilter, i18n_analyzer, BoolBooster, FunctionBooster

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
        'followers': Sort('nb_followers'),
    }
    filters = {
        'reuses': RangeFilter('nb_reuses'),
        'datasets': RangeFilter('nb_datasets'),
        'followers': RangeFilter('nb_followers'),
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
            'nb_stars': {'type': 'integer'},
            'nb_followers': {'type': 'integer'},
            'org_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': True,
            },
        }
    }
    boosters = [
        BoolBooster('public_service', 1.1),
        FunctionBooster('_score * (1 + sqrt(0.01 * doc["nb_reuses"].value))'),
        FunctionBooster('_score * (1 + sqrt(0.01 * doc["nb_datasets"].value))'),
        # ValueBooster('nb_reuses', 'sqrt'),
        # ValueBooster('nb_datasets', 'sqrt'),
    ]

    @classmethod
    def serialize(cls, organization):
        return {
            'name': organization.name,
            'description': organization.description,
            'url': organization.url,
            'nb_datasets': organization.metrics.get('datasets', 0),
            'nb_reuses': organization.metrics.get('reuses', 0),
            'nb_stars': organization.metrics.get('stars', 0),
            'nb_followers': organization.metrics.get('followers', 0),
            'org_suggest': {
                'input': [organization.name] + [
                    n for n in organization.name.split(' ')
                    if len(n) > 3
                ],
                'output': organization.name,
                'payload': {
                    'id': str(organization.id),
                    'image_url': organization.image_url,
                    'slug': organization.slug,
                },
            },
            'public_service': organization.public_service,  # TODO: extract tis into plugin
        }
