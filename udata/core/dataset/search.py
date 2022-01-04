from udata.models import (
    Dataset, Organization, User, GeoZone, License
)
from udata.search import (
    ModelSearchAdapter, register,
    ModelTermsFilter, BoolFilter, Filter,
    TemporalCoverageFilter
)


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
