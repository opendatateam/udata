from elasticsearch_dsl import (
    Boolean, Completion, Date, Long, Object, String, Nested
)

from udata.core.site.models import current_site
from udata.core.spatial.models import (
    admin_levels, spatial_granularities, ADMIN_LEVEL_MAX
)
from udata.i18n import lazy_gettext as _
from udata.models import (
    Dataset, Organization, License, User, GeoZone, RESOURCE_TYPES
)
from udata.search import (
    ModelSearchAdapter, i18n_analyzer, register,
    lazy_config
)
from udata.search.analysis import simple
from udata.search.fields import (
    TermsFacet, ModelTermsFacet, RangeFacet, TemporalCoverageFacet,
    BoolBooster, GaussDecay, BoolFacet, ValueFactor
)
from udata.utils import to_iso_datetime


__all__ = ('DatasetSearch', )


DEFAULT_SPATIAL_WEIGHT = 1
DEFAULT_TEMPORAL_WEIGHT = 1
lazy = lazy_config('dataset')


def max_reuses():
    return max(current_site.get_metrics()['max_dataset_reuses'], 10)


def max_followers():
    return max(current_site.get_metrics()['max_dataset_followers'], 10)


def granularity_labelizer(value):
    return dict(spatial_granularities).get(value)


def zone_labelizer(value):
    if isinstance(value, str):
        return GeoZone.objects(id=value).first()
    elif isinstance(value, GeoZone):
        return value


def dataset_badge_labelizer(kind):
    return Dataset.__badges__.get(kind, '')


def resource_type_labelizer(value):
    return RESOURCE_TYPES.get(value)


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
        'format': String(index='not_analyzed'),
        'schema': String(index='not_analyzed'),
        'schema_version': String(index='not_analyzed'),
    })
    format_suggest = Completion(analyzer=simple,
                                search_analyzer=simple,
                                payloads=False)
    dataset_suggest = Completion(analyzer=simple,
                                 search_analyzer=simple,
                                 payloads=True)
    mime_suggest = Completion(analyzer=simple,
                              search_analyzer=simple,
                              payloads=False)
    created = Date(format='date_hour_minute_second')
    last_modified = Date(format='date_hour_minute_second')
    metrics = Dataset.__search_metrics__
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
        'schema': TermsFacet(field='resources.schema'),
        'schema_version': TermsFacet(field='resources.schema_version'),
        'resource_type': TermsFacet(field='resources.type',
                                    labelizer=resource_type_labelizer),
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
        BoolBooster('featured', lazy('featured_boost')),
        BoolBooster('from_certified', lazy('certified_boost')),
        ValueFactor('spatial_weight', missing=1),
        ValueFactor('temporal_weight', missing=1),
        GaussDecay('metrics.reuses', max_reuses, decay=lazy('reuses_decay')),
        GaussDecay('metrics.followers', max_followers, max_followers,
                   decay=lazy('followers_decay')),
    ]

    @classmethod
    def is_indexable(cls, dataset):
        return (dataset.deleted is None and dataset.archived is None and
                len(dataset.resources) > 0 and
                not dataset.private)

    @classmethod
    def get_suggest_weight(cls, temporal_weight, spatial_weight, featured):
        '''Compute the suggest part of the indexation payload'''
        featured_weight = 1 if not featured else cls.from_config('FEATURED_WEIGHT')
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
                    'type': r.type,
                    'schema': dict(r.schema).get('name', {}),
                    'schema_version': dict(r.schema).get('version', {}),
                }
                for r in dataset.resources],
            'format_suggest': [r.format.lower()
                               for r in dataset.resources
                               if r.format],
            'mime_suggest': [],  # Need a custom loop below
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
            'created': to_iso_datetime(dataset.created_at),
            'last_modified': to_iso_datetime(dataset.last_modified),
            'metrics': dataset.metrics,
            'featured': dataset.featured,
            'from_certified': certified,
        }
        if (dataset.temporal_coverage is not None and
                dataset.temporal_coverage.start and
                dataset.temporal_coverage.end):
            start = dataset.temporal_coverage.start.toordinal()
            end = dataset.temporal_coverage.end.toordinal()
            temporal_weight = min(abs(end - start) / 365, cls.from_config('MAX_TEMPORAL_WEIGHT'))
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

        # mime Completion
        mimes = {r.mime.lower() for r in dataset.resources if r.mime}
        for mime in mimes:
            document['mime_suggest'].append({
                'input': mime.replace('+', '/').split('/') + [mime],
                'output': mime,
            })

        return document
