import datetime
from udata.models import (
    Dataset, Organization, User, GeoZone, License, Topic
)
from udata.search import (
    ModelSearchAdapter, register,
    ModelTermsFilter, BoolFilter, Filter,
    TemporalCoverageFilter
)
from udata.core.spatial.models import (
    admin_levels, ADMIN_LEVEL_MAX
)
from udata.core.dataset.api import DatasetApiParser, DEFAULT_SORTING
from udata.utils import to_iso_datetime

__all__ = ('DatasetSearch', )


@register
class DatasetSearch(ModelSearchAdapter):
    model = Dataset
    search_url = 'datasets/'

    sorts = {
        'created': 'created_at_internal',
        'last_update': 'last_modified_internal',
        'reuses': 'metrics.reuses',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
    }

    filters = {
        'tag': Filter(),
        'badge': Filter(),
        'organization': ModelTermsFilter(model=Organization),
        'owner': ModelTermsFilter(model=User),
        'license': ModelTermsFilter(model=License),
        'geozone': ModelTermsFilter(model=GeoZone),
        'granularity': Filter(),
        'format': Filter(),
        'schema': Filter(),
        'temporal_coverage': TemporalCoverageFilter(),
        'featured': BoolFilter(),
        'topic': ModelTermsFilter(model=Topic),
    }

    @classmethod
    def is_indexable(cls, dataset):
        return (dataset.deleted is None and dataset.archived is None and
                len(dataset.resources) > 0 and
                not dataset.private)

    @classmethod
    def mongo_search(cls, args):
        datasets = Dataset.objects(archived=None, deleted=None, private=False)
        datasets = DatasetApiParser.parse_filters(datasets, args)

        sort = cls.parse_sort(args['sort']) or ('$text_score' if args['q'] else None) or DEFAULT_SORTING
        offset = (args['page'] - 1) * args['page_size']
        return datasets.order_by(sort).skip(offset).limit(args['page_size']), datasets.count()

    @classmethod
    def serialize(cls, dataset):
        organization = None
        owner = None

        topics = Topic.objects(datasets=dataset)

        if dataset.organization:
            org = Organization.objects(id=dataset.organization.id).first()
            organization = {
                'id': str(org.id),
                'name': org.name,
                'public_service': 1 if org.public_service else 0,
                'followers': org.metrics.get('followers', 0)
            }
        elif dataset.owner:
            owner = User.objects(id=dataset.owner.id).first()

        document = {
            'id': str(dataset.id),
            'title': dataset.title,
            'description': dataset.description,
            'acronym': dataset.acronym or None,
            'url': dataset.display_url,
            'tags': dataset.tags,
            'license': getattr(dataset.license, 'id', None),
            'badges': [badge.kind for badge in dataset.badges],
            'frequency': dataset.frequency,
            'created_at': to_iso_datetime(dataset.created_at),
            'last_update': to_iso_datetime(dataset.last_update),
            'views': dataset.metrics.get('views', 0),
            'followers': dataset.metrics.get('followers', 0),
            'reuses': dataset.metrics.get('reuses', 0),
            'featured': 1 if dataset.featured else 0,
            'resources_count': len(dataset.resources),
            'organization': organization,
            'owner': str(owner.id) if owner else None,
            'format': [r.format.lower() for r in dataset.resources if r.format],
            'schema': [r.schema.get('name') for r in dataset.resources if r.schema],
            'topics': [str(t.id) for t in topics if topics],
        }
        extras = {}
        for key, value in dataset.extras.items():
            extras[key] = to_iso_datetime(value) if isinstance(value, datetime.datetime) else value
        document.update({'extras': extras})
        if dataset.harvest:
            harvest = {}
            for key, value in dataset.harvest._data.items():
                harvest[key] = to_iso_datetime(value) if isinstance(value, datetime.datetime) else value
            document.update({'harvest': harvest})

        if (dataset.temporal_coverage is not None and
                dataset.temporal_coverage.start and
                dataset.temporal_coverage.end):
            start = to_iso_datetime(dataset.temporal_coverage.start)
            end = to_iso_datetime(dataset.temporal_coverage.end)
            document.update({
                'temporal_coverage_start': start,
                'temporal_coverage_end': end,
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
            document.update({
                'geozones': geozones,
                'granularity': dataset.spatial.granularity,
            })
        return document
