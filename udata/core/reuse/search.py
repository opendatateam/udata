# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Reuse, Organization, REUSE_TYPES
from udata.search import ModelSearchAdapter, Sort, i18n_analyzer
from udata.search import RangeFacet, BoolFacet
from udata.search import TermFacet, ModelTermFacet
from udata.search import BoolBooster, GaussDecay


__all__ = ('ReuseSearch', )


class ReuseTypeFacet(TermFacet):
    def labelize(self, value):
        return REUSE_TYPES[value]


class ReuseSearch(ModelSearchAdapter):
    model = Reuse
    fields = (
        'title^3',
        'description^2',
        'datasets.title',
    )
    facets = {
        'tag': TermFacet('tags'),
        'organization': ModelTermFacet('organization', Organization),
        'type': ReuseTypeFacet('type'),
        'datasets': RangeFacet('metrics.datasets'),
        'stars': RangeFacet('metrics.stars'),
        'followers': RangeFacet('metrics.followers'),
        'featured': BoolFacet('featured'),
    }
    sorts = {
        'title': Sort('title.raw'),
        'created': Sort('created'),
        'last_modified': Sort('last_modified'),
        'datasets': Sort('metrics.datasets'),
        'stars': Sort('metrics.stars'),
        'followers': Sort('metrics.followers'),
    }
    mapping = {
        'properties': {
            'title': {
                'type': 'string',
                'analyzer': i18n_analyzer,
                'fields': {
                    'raw': {'type': 'string', 'index': 'not_analyzed'}
                }
            },
            'description': {'type': 'string', 'analyzer': i18n_analyzer},
            'url': {'type': 'string'},
            'organization': {'type': 'string'},
            'type': {'type': 'string'},
            'tags': {'type': 'string', 'index_name': 'tag', 'index': 'not_analyzed'},
            'tag_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': False,
            },
            'created': {'type': 'date', 'format': 'date_hour_minute_second'},
            'last_modified': {'type': 'date', 'format': 'date_hour_minute_second'},
            'datasets': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'}
                }
            },
            'metrics': {'type': 'object', 'index_name': 'metrics'},
            'featured': {'type': 'boolean'},
            'reuse_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': True,
            },
        }
    }
    boosters = [
        BoolBooster('featured', 1.1),
        GaussDecay('metrics.datasets', 30, decay=0.8),
        GaussDecay('metrics.followers', 200, decay=0.8),
    ]

    @classmethod
    def serialize(cls, reuse):
        '''By default use the ``to_dict`` method and exclude ``_id``, ``_cls`` and ``owner`` fields'''
        return {
            'title': reuse.title,
            'description': reuse.description,
            'url': reuse.url,
            'organization': str(reuse.organization.id) if reuse.organization else None,
            'type': reuse.type,
            'tags': reuse.tags,
            'tag_suggest': reuse.tags,
            'created': reuse.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'last_modified': reuse.last_modified.strftime('%Y-%m-%dT%H:%M:%S'),
            'datasets': [
                {'title': d.title} for d in reuse.datasets
            ],
            'metrics': reuse.metrics,
            'featured': reuse.featured,
            'reuse_suggest': {
                'input': [reuse.title] + [
                    n for n in reuse.title.split(' ')
                    if len(n) > 3
                ],
                'output': reuse.title,
                'payload': {
                    'id': str(reuse.id),
                    'slug': reuse.slug,
                    'image_url': reuse.image_url,
                },
            },
        }
