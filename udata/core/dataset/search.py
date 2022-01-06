from udata.models import (
    Dataset, Organization, User, GeoZone, License
)
from udata.search import (
    ModelSearchAdapter, register,
    ModelTermsFilter, BoolFilter, Filter,
    TemporalCoverageFilter
)
from udata.utils import to_iso_datetime

__all__ = ('DatasetSearch', )


DEFAULT_SPATIAL_WEIGHT = 1
DEFAULT_TEMPORAL_WEIGHT = 1


@register
class DatasetSearch(ModelSearchAdapter):
    model = Dataset
    search_url = 'datasets/'

    sorts = {
        'title': 'title.raw',
        'created': 'created',
        'last_modified': 'last_modified',
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
        'resource_type': Filter(),
        'temporal_coverage': TemporalCoverageFilter(),
        'featured': BoolFilter(),
    }

    @classmethod
    def is_indexable(cls, dataset):
        return (dataset.deleted is None and dataset.archived is None and
                len(dataset.resources) > 0 and
                not dataset.private)

    @classmethod
    def serialize(cls, dataset):
        return {
            'id': str(dataset.id),
            'title': dataset.title,
            'description': dataset.description,
            'acronym': dataset.acronym or None,
            'url': dataset.display_url,
            'created_at': to_iso_datetime(dataset.created_at),
            'orga_sp': 1 if dataset.organization and dataset.organization.public_service else 0,
            'orga_followers': dataset.organization.metrics.get('followers', 0) if dataset.organization else 0,
            'dataset_views': dataset.metrics.get('views', 0),
            'dataset_followers': dataset.metrics.get('followers', 0),
            'dataset_reuses': dataset.metrics.get('reuses', 0),
            'dataset_featured': 1 if dataset.featured else 0,
            'resources_count': len(dataset.resources),
            'concat_title_org': f"{dataset.title} {dataset.acronym if dataset.acronym else ''} {dataset.organization.name if dataset.organization else dataset.owner.fullname}",
            'organization_id': str(dataset.organization.id) if dataset.organization else str(dataset.owner.id),
            'temporal_coverage_start': 0,
            'temporal_coverage_end': 0,
            'spatial_granularity': 0,
            'spatial_zones': 0
        }
