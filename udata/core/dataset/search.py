# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.site.views import current_site

from udata.models import Dataset, Organization, License, Territory, SPATIAL_GRANULARITIES
from udata.search import ModelSearchAdapter, i18n_analyzer, metrics_mapping
from udata.search.fields import Sort, BoolFacet, TemporalCoverageFacet, ExtrasFacet
from udata.search.fields import TermFacet, ModelTermFacet, RangeFacet
from udata.search.fields import BoolBooster, GaussDecay

# Metrics are require for dataset search
from . import metrics  # noqa

__all__ = ('DatasetSearch', )


max_reuses = lambda: max(current_site.metrics.get('max_dataset_reuses'), 10)
max_followers = lambda: max(current_site.metrics.get('max_dataset_followers'), 10)


class DatasetSearch(ModelSearchAdapter):
    model = Dataset
    fuzzy = True
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
            'metrics': metrics_mapping(Dataset),
            'featured': {'type': 'boolean'},
            'temporal_coverage': {  # Store dates as ordinals to handle pre-1900 dates
                'type': 'object',
                'properties': {
                    'start': {'type': 'long'},
                    'end': {'type': 'long'},
                }
            },
            'territories': {
                'type': 'object',
                'index_name': 'territories',
                'properties': {
                    'id': {'type': 'string'},
                    'name': {'type': 'string'},
                    'code': {'type': 'string'},
                }
            },
            'granularity': {'type': 'string', 'index': 'not_analyzed'},
            'geom': {
                'type': 'geo_shape',
                'precision': '100m',
            },
            'extras': {
                'type': 'object',
                'index_name': 'extra',
            },
        }
    }
    fields = (
        'title^6',
        'tags^3',
        'territories.name^3',
        'description',
        'code',
    )
    sorts = {
        'title': Sort('title.raw'),
        'created': Sort('created'),
        'last_modified': Sort('last_modified'),
        'reuses': Sort('metrics.reuses'),
        'followers': Sort('metrics.followers'),
    }
    facets = {
        'tag': TermFacet('tags'),
        'organization': ModelTermFacet('organization', Organization),
        'supplier': ModelTermFacet('supplier', Organization),
        'license': ModelTermFacet('license', License),
        'territory': ModelTermFacet('territories.id', Territory),
        'granularity': TermFacet('granularity', lambda l, v: SPATIAL_GRANULARITIES[v]),
        'format': TermFacet('resources.format'),
        'reuses': RangeFacet('metrics.reuses'),
        'temporal_coverage': TemporalCoverageFacet('temporal_coverage'),
        'featured': BoolFacet('featured'),
        'extra': ExtrasFacet('extras'),
    }
    boosters = [
        BoolBooster('featured', 1.1),
        BoolBooster('from_public_service', 1.3),
        GaussDecay('metrics.reuses', max_reuses, decay=0.8),
        GaussDecay('metrics.followers', max_followers, max_followers, decay=0.8),
    ]

    @classmethod
    def is_indexable(cls, dataset):
        return dataset.deleted is None and len(dataset.resources) > 0 and not dataset.private

    @classmethod
    def serialize(cls, dataset):
        org_id = str(dataset.organization.id) if dataset.organization is not None else None
        supplier_id = str(dataset.supplier.id) if dataset.supplier is not None else None
        supplier_id = supplier_id if supplier_id != org_id else None
        image_url = dataset.organization.image_url if dataset.organization and dataset.organization.image_url else None

        document = {
            'title': dataset.title,
            'description': dataset.description,
            'license': dataset.license.id if dataset.license is not None else None,
            'tags': dataset.tags,
            'tag_suggest': dataset.tags,
            'resources': [
                {
                    'title': r.title,
                    'description': r.description,
                    'format': r.format,
                }
                for r in dataset.resources],
            'format_suggest': [r.format.lower() for r in dataset.resources if r.format],
            'frequency': dataset.frequency,
            'organization': org_id,
            'supplier': supplier_id,
            'dataset_suggest': {
                'input': cls.completer_tokenize(dataset.title),
                'output': dataset.title,
                'payload': {
                    'id': str(dataset.id),
                    'slug': dataset.slug,
                    'image_url': image_url,
                },
            },
            'created': dataset.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'last_modified': dataset.last_modified.strftime('%Y-%m-%dT%H:%M:%S'),
            'metrics': dataset.metrics,
            'extras': dataset.extras,
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

        if dataset.spatial is not None:
            document.update({
                'territories': [{'id': str(t.id), 'name': t.name, 'code': t.code} for t in dataset.spatial.territories],
                'geom': dataset.spatial.geom,
                'granularity': dataset.spatial.granularity,
            })

        return document
