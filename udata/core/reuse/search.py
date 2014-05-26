# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Reuse, Organization
from udata.search import ModelSearchAdapter, Sort, i18n_analyzer
from udata.search import RangeFilter, BoolFilter
from udata.search import TermFacet, ModelTermFacet
from udata.search import BoolBooster, FunctionBooster


__all__ = ('ReuseSearch', )


class ReuseSearch(ModelSearchAdapter):
    model = Reuse
    fields = (
        'title^2',
        'description',
    )
    facets = {
        'tag': TermFacet('tags'),
        'organization': ModelTermFacet('organization', Organization),
        'type': TermFacet('type'),
    }
    sorts = {
        'title': Sort('title.raw'),
        'created': Sort('created'),
        'last_modified': Sort('last_modified'),
        'datasets': Sort('nb_datasets'),
        'stars': Sort('nb_stars'),
        'followers': Sort('nb_followers'),
    }
    filters = {
        'datasets': RangeFilter('nb_datasets'),
        'stars': RangeFilter('nb_stars'),
        'followers': RangeFilter('nb_followers'),
        'featured': BoolFilter('featured'),
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
            'nb_datasets': {'type': 'integer'},
            'nb_stars': {'type': 'integer'},
            'nb_followers': {'type': 'integer'},
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
        FunctionBooster('_score * (1 + sqrt(0.01 * doc["nb_datasets"].value))'),
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
            'nb_datasets': reuse.metrics.get('datasets', 0),
            'nb_stars': reuse.metrics.get('stars', 0),
            'nb_followers': reuse.metrics.get('followers', 0),
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
