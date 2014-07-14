# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Organization
from udata.search import ModelSearchAdapter, Sort, RangeFacet, i18n_analyzer, BoolBooster, GaussDecay

from . import metrics  # Metrics are need for the mapping

__all__ = ('OrganizationSearch', )


class OrganizationSearch(ModelSearchAdapter):
    model = Organization
    fields = (
        'name^2',
        'description',
    )
    sorts = {
        'name': Sort('name.raw'),
        'reuses': Sort('metrics.reuses'),
        'datasets': Sort('metrics.datasets'),
        'followers': Sort('metrics.followers'),
    }
    facets = {
        'reuses': RangeFacet('metrics.reuses'),
        'datasets': RangeFacet('metrics.datasets'),
        'followers': RangeFacet('metrics.followers'),
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
            'metrics': {'type': 'object', 'index_name': 'metrics'},
            'org_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': True,
            },
        }
    }
    boosters = [
        BoolBooster('public_service', 1.5),
        GaussDecay('metrics.followers', 200, decay=0.8),
        GaussDecay('metrics.reuses', 50, decay=0.9),
        GaussDecay('metrics.datasets', 50, decay=0.9),
    ]

    @classmethod
    def is_indexable(cls, org):
        return org.deleted is None

    @classmethod
    def serialize(cls, organization):
        return {
            'name': organization.name,
            'description': organization.description,
            'url': organization.url,
            'metrics': organization.metrics,
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
