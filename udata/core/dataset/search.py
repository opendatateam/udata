# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Dataset, Organization, License
from udata.search import ModelSearchAdapter, i18n_analyzer
from udata.search.fields import Sort, BoolFacet, TemporalCoverageFacet
from udata.search.fields import TermFacet, ModelTermFacet, RangeFacet
from udata.search.fields import BoolBooster, GaussDecay

__all__ = ('DatasetSearch', )


class DatasetSearch(ModelSearchAdapter):
    model = Dataset
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
            'license': {'type': 'string', 'index': 'not_analyzed'},
            'frequency': {'type': 'string'},
            'organization': {'type': 'string'},
            'supplier': {'type': 'string'},
            'tags': {'type': 'string', 'index_name': 'tag', 'index': 'not_analyzed'},
            'tag_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': False,
            },
            'resources': {
                'type': 'object',
                'index_name': 'resource',
                'properties': {
                    'title': {'type': 'string'},
                    'description': {'type': 'string'},
                    'license': {'type': 'string'},
                }
            },
            'format_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': False,
            },
            'dataset_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': True,
            },
            'created': {'type': 'date', 'format': 'date_hour_minute_second'},
            'last_modified': {'type': 'date', 'format': 'date_hour_minute_second'},
            'nb_reuses': {'type': 'integer'},
            'nb_followers': {'type': 'integer'},
            'featured': {'type': 'boolean'},
            'temporal_coverage': {  # Store dates as ordinals to handle pre-1900 dates
                'type': 'object',
                'properties': {
                    'start': {'type': 'long'},
                    'end': {'type': 'long'},
                }
            },
        }
    }
    fields = (
        'title^3',
        'description',
        'tags',
    )
    sorts = {
        'title': Sort('title.raw'),
        'created': Sort('created'),
        'last_modified': Sort('last_modified'),
        'reuses': Sort('nb_reuses'),
        'followers': Sort('nb_followers'),
    }
    facets = {
        'tag': TermFacet('tags'),
        'organization': ModelTermFacet('organization', Organization),
        'supplier': ModelTermFacet('supplier', Organization),
        'license': ModelTermFacet('license', License),
        'format': TermFacet('resources.format'),
        'reuses': RangeFacet('nb_reuses'),
        'temporal_coverage': TemporalCoverageFacet('temporal_coverage'),
        'featured': BoolFacet('featured'),
    }
    boosters = [
        BoolBooster('featured', 1.1),
        BoolBooster('from_public_service', 1.3),
        GaussDecay('nb_reuses', 50, decay=0.8),
        GaussDecay('nb_followers', 200, 200, decay=0.8),
    ]

    @classmethod
    def serialize(cls, dataset):
        image_url = dataset.organization.image_url if dataset.organization and dataset.organization.image_url else None
        document = {
            'title': dataset.title,
            'description': dataset.description,
            'license': dataset.license.id if dataset.license else None,
            'tags': dataset.tags,
            'tag_suggest': dataset.tags,
            'resources': [
                {
                    'title': r.title,
                    'description': r.description,
                    'format': r.format,
                }
                for r in dataset.resources],
            'format_suggest': [r.format.lower() for r in dataset.resources],
            'frequency': dataset.frequency,
            'organization': str(dataset.organization.id) if dataset.organization else None,
            'supplier': str(dataset.supplier.id) if dataset.supplier else None,
            'dataset_suggest': {
                'input': [dataset.title] + [
                    n for n in dataset.title.split(' ')
                    if len(n) > 3
                ],
                'output': dataset.title,
                'payload': {
                    'id': str(dataset.id),
                    'slug': dataset.slug,
                    'image_url': image_url,
                },
            },
            'created': dataset.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'last_modified': dataset.last_modified.strftime('%Y-%m-%dT%H:%M:%S'),
            'nb_reuses': dataset.metrics.get('reuses', 0),
            'nb_followers': dataset.metrics.get('followers', 0),
            'featured': dataset.featured,
            'from_public_service': dataset.organization.public_service if dataset.organization else False,  # TODO: extract tis into plugin
        }
        if dataset.temporal_coverage is not None and dataset.temporal_coverage.start and dataset.temporal_coverage.end:
            document.update({
                'temporal_coverage': {
                    'start': dataset.temporal_coverage.start.toordinal(),
                    'end': dataset.temporal_coverage.end.toordinal(),
                }
            })
        return document
