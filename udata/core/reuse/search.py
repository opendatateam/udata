from udata.models import (
    Reuse, Organization, Dataset, User
)
from udata.search import (
    ModelSearchAdapter, register,
    ModelTermsFilter, BoolFilter, Filter
)
from udata.utils import to_iso_datetime


__all__ = ('ReuseSearch', )


@register
class ReuseSearch(ModelSearchAdapter):
    model = Reuse
    search_url = 'reuses/'

    sorts = {
        'title': 'title.raw',
        'created': 'created',
        'last_modified': 'last_modified',
        'datasets': 'metrics.datasets',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
    }

    filters = {
        'tag': Filter(),
        'organization': ModelTermsFilter(model=Organization),
        'owner': ModelTermsFilter(model=User),
        'dataset': ModelTermsFilter(model=Dataset),
        'type': Filter(),
        'badge': Filter(),
        'featured': BoolFilter(),
        'topic': Filter(),
    }

    @classmethod
    def is_indexable(cls, reuse):
        return (reuse.deleted is None and
                len(reuse.datasets) > 0 and
                not reuse.private)

    @classmethod
    def serialize(cls, reuse):
        return {
            'id': str(reuse.id),
            'title': reuse.title,
            'description': reuse.description,
            'url': reuse.url,
            'created_at': to_iso_datetime(reuse.created_at),
            'orga_followers': reuse.organization.metrics.get('followers', 0) if reuse.organization else reuse.owner.metrics.get('followers', 0),
            'reuse_views': reuse.metrics.get('views', 0),
            'reuse_followers': reuse.metrics.get('followers', 0),
            'reuse_datasets': reuse.metrics.get('datasets', 0),
            'reuse_featured': 1 if reuse.featured else 0,
            'organization_id': str(reuse.organization.id) if reuse.organization else str(reuse.owner.id)
        }
