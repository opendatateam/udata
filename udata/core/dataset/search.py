# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from elasticsearch_dsl import (
    Boolean, Completion, Date, Long, Object, String, Nested
)

from udata.i18n import lazy_gettext as _
from udata.core.site.models import current_site
from udata.models import (
    Dataset, Organization, License, User, GeoZone
)
from udata.search import (
    ModelSearchAdapter, i18n_analyzer, metrics_mapping_for, register,
)
from udata.search.fields import (
    TermsFacet, ModelTermsFacet, RangeFacet, TemporalCoverageFacet,
    BoolBooster, GaussDecay, BoolFacet, ValueFactor
)
from udata.search.analysis import simple

from udata.core.spatial.models import (
    admin_levels, spatial_granularities, ADMIN_LEVEL_MAX
)

# Metrics are require for dataset search
from . import metrics  # noqa

__all__ = ('DatasetSearch', )


# After this number of years, scoring is kept constant instead of increasing.
MAX_TEMPORAL_WEIGHT = 5
DEFAULT_SPATIAL_WEIGHT = 1
DEFAULT_TEMPORAL_WEIGHT = 1
FEATURED_WEIGHT = 3


def max_reuses():
    return max(current_site.metrics.get('max_dataset_reuses'), 10)


def max_followers():
    return max(current_site.metrics.get('max_dataset_followers'), 10)


def granularity_labelizer(value):
    return dict(spatial_granularities).get(value)


def zone_labelizer(value):
    if value and isinstance(value, basestring):
        return GeoZone.objects(id=value).first() or value
    return value


def dataset_badge_labelizer(kind):
    return Dataset.__badges__.get(kind, '')


@register
class DatasetSearch(ModelSearchAdapter):
    model = Dataset
    fuzzy = True
    exclude_fields = ['spatial.geom', 'spatial.zones.geom']

    class Meta:
        doc_type = 'Dataset'

    title = String(analyzer=i18n_analyzer, fields={
        'raw': String(index='not_analyzed')
    })
    description = String(analyzer=i18n_analyzer)
    license = String(index='not_analyzed')
    frequency = String(index='not_analyzed')
    organization = String(index='not_analyzed')
    owner = String(index='not_analyzed')
    tags = String(index='not_analyzed', fields={
        'i18n': String(index='not_analyzed')
    })
    badges = String(index='not_analyzed')
    tag_suggest = Completion(analyzer=simple,
                             search_analyzer=simple,
                             payloads=False)
    resources = Object(properties={
        'title': String(),
        'description': String(),
        'format': String(index='not_analyzed')
    })
    format_suggest = Completion(analyzer=simple,
                                search_analyzer=simple,
                                payloads=False)
    dataset_suggest = Completion(analyzer=simple,
                                 search_analyzer=simple,
                                 payloads=True)
    created = Date(format='date_hour_minute_second')
    last_modified = Date(format='date_hour_minute_second')
    metrics = metrics_mapping_for(Dataset)
    featured = Boolean()
    temporal_coverage = Nested(multi=False, properties={
        'start': Long(),
        'end': Long()
    })
    temporal_weight = Long(),
    geozones = Object(properties={
        'id': String(index='not_analyzed'),
        'name': String(index='not_analyzed'),
        'keys': String(index='not_analyzed')
    })
    granularity = String(index='not_analyzed')
    spatial_weight = Long()
    from_certified = Boolean()

    fields = (
        'geozones.keys^9',
        'geozones.name^9',
        'acronym^7',
        'title^6',
        'tags.i18n^3',
        'description',
    )
    sorts = {
        'title': 'title.raw',
        'created': 'created',
        'last_modified': 'last_modified',
        'reuses': 'metrics.reuses',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
    }

    facets = {
        'tag': TermsFacet(field='tags'),
        'badge': TermsFacet(field='badges', labelizer=dataset_badge_labelizer),
        'organization': ModelTermsFacet(field='organization',
                                        model=Organization),
        'owner': ModelTermsFacet(field='owner', model=User),
        'license': ModelTermsFacet(field='license', model=License),
        'geozone': ModelTermsFacet(field='geozones.id', model=GeoZone,
                                   labelizer=zone_labelizer),
        'granularity': TermsFacet(field='granularity',
                                  labelizer=granularity_labelizer),
        'format': TermsFacet(field='resources.format'),
        'reuses': RangeFacet(field='metrics.reuses',
                             ranges=[('none', (None, 1)),
                                     ('few', (1, 5)),
                                     ('quite', (5, 10)),
                                     ('many', (10, None))],
                             labels={
                                 'none': _('Never reused'),
                                 'few': _('Little reused'),
                                 'quite': _('Quite reused'),
                                 'many': _('Heavily reused'),
                             }),
        'temporal_coverage': TemporalCoverageFacet(field='temporal_coverage'),
        'featured': BoolFacet(field='featured'),
    }
    boosters = [
        BoolBooster('featured', 1.5),
        BoolBooster('from_certified', 1.2),
        ValueFactor('spatial_weight', missing=1),
        ValueFactor('temporal_weight', missing=1),
        GaussDecay('metrics.reuses', max_reuses, decay=0.1),
        GaussDecay(
            'metrics.followers', max_followers, max_followers, decay=0.1),
    ]

    @classmethod
    def is_indexable(cls, dataset):
        return (dataset.deleted is None and
                len(dataset.resources) > 0 and
                not dataset.private)

    @classmethod
    def get_suggest_weight(cls, temporal_weight, spatial_weight, featured):
        '''Compute the suggest part of the indexation payload'''
        featured_weight = 1 if not featured else FEATURED_WEIGHT
        return int(temporal_weight * spatial_weight * featured_weight * 10)

    @classmethod
    def serialize(cls, dataset):
        organization = None
        owner = None
        image_url = None
        spatial_weight = DEFAULT_SPATIAL_WEIGHT
        temporal_weight = DEFAULT_TEMPORAL_WEIGHT

        if dataset.organization:
            organization = Organization.objects(id=dataset.organization.id).first()
            image_url = organization.logo(40, external=True)
        elif dataset.owner:
            owner = User.objects(id=dataset.owner.id).first()
            image_url = owner.avatar(40, external=True)

        certified = organization and organization.certified

        document = {
            'title': dataset.title,
            'description': dataset.description,
            'license': getattr(dataset.license, 'id', None),
            'tags': dataset.tags,
            'badges': [badge.kind for badge in dataset.badges],
            'tag_suggest': dataset.tags,
            'resources': [
                {
                    'title': r.title,
                    'description': r.description,
                    'format': r.format,
                }
                for r in dataset.resources],
            'format_suggest': [r.format.lower()
                               for r in dataset.resources
                               if r.format],
            'frequency': dataset.frequency,
            'organization': str(organization.id) if organization else None,
            'owner': str(owner.id) if owner else None,
            'dataset_suggest': {
                'input': cls.completer_tokenize(dataset.title) + [str(dataset.id)],
                'output': dataset.title,
                'payload': {
                    'id': str(dataset.id),
                    'slug': dataset.slug,
                    'acronym': dataset.acronym,
                    'image_url': image_url,
                },
            },
            'created': dataset.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'last_modified': dataset.last_modified.strftime(
                '%Y-%m-%dT%H:%M:%S'),
            'metrics': dataset.metrics,
            'featured': dataset.featured,
            'from_certified': certified,
        }
        if (dataset.temporal_coverage is not None and
                dataset.temporal_coverage.start and
                dataset.temporal_coverage.end):
            start = dataset.temporal_coverage.start.toordinal()
            end = dataset.temporal_coverage.end.toordinal()
            temporal_weight = min((end - start) / 365, MAX_TEMPORAL_WEIGHT)
            document.update({
                'temporal_coverage': {'start': start, 'end': end},
                'temporal_weight': temporal_weight,
            })

        if dataset.spatial is not None:
            # Index precise zone labels and parents zone identifiers
            # to allow fast filtering.
            zone_ids = [z.id for z in dataset.spatial.zones]
            zones = GeoZone.objects(id__in=zone_ids).exclude('geom')
            parents = set()
            geozones = []
            coverage_level = ADMIN_LEVEL_MAX
            for zone in zones:
                geozones.append({
                    'id': zone.id,
                    'name': zone.name,
                    'keys': zone.keys_values
                })
                parents |= set(zone.parents)
                coverage_level = min(coverage_level, admin_levels[zone.level])

            geozones.extend([{'id': p} for p in parents])

            spatial_weight = ADMIN_LEVEL_MAX / coverage_level
            document.update({
                'geozones': geozones,
                'granularity': dataset.spatial.granularity,
                'spatial_weight': spatial_weight,
            })

        document['dataset_suggest']['weight'] = cls.get_suggest_weight(
            temporal_weight, spatial_weight, dataset.featured)

        if dataset.acronym:
            document['dataset_suggest']['input'].append(dataset.acronym)

        return document
