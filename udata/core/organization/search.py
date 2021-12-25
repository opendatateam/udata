from udata import search
from udata.models import Organization
from udata.search.fields import Filter


__all__ = ('OrganizationSearch', )


@search.register
class OrganizationSearch(search.ModelSearchAdapter):
    model = Organization
    search_url = 'http://127.0.0.1:8000/api/v1/organizations/'

    sorts = {
        'name': 'name.raw',
        'reuses': 'metrics.reuses',
        'datasets': 'metrics.datasets',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
        'created': 'created',
        'last_modified': 'last_modified',
    }

    filters = {
        'badge': Filter()
    }

    @classmethod
    def is_indexable(cls, org):
        return org.deleted is None
