from udata.models import (
    Reuse, Organization, Dataset, User
)
from udata.search import (
    ModelSearchAdapter, register,
    ModelTermsFilter, BoolFilter, Filter
)


__all__ = ('ReuseSearch', )


@register
class ReuseSearch(ModelSearchAdapter):
    model = Reuse
    search_url = 'http://127.0.0.1:8000/api/v1/reuses/'

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
