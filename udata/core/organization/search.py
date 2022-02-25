import datetime
from udata import search
from udata.models import Organization
from udata.search.fields import Filter
from udata.utils import to_iso_datetime


__all__ = ('OrganizationSearch', )


@search.register
class OrganizationSearch(search.ModelSearchAdapter):
    model = Organization
    search_url = 'organizations/'

    sorts = {
        'reuses': 'metrics.reuses',
        'datasets': 'metrics.datasets',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
        'created': 'created'
    }

    filters = {
        'badge': Filter()
    }

    @classmethod
    def is_indexable(cls, org):
        return org.deleted is None

    @classmethod
    def serialize(cls, organization):
        extras = {}
        for key, value in organization.extras.items():
            extras[key] = to_iso_datetime(value) if isinstance(value, datetime.datetime) else value
        return {
            'id': str(organization.id),
            'name': organization.name,
            'acronym': organization.acronym if organization.acronym else None,
            'description': organization.description,
            'url': organization.url,
            'badges': [badge.kind for badge in organization.badges],
            'created_at': to_iso_datetime(organization.created_at),
            'orga_sp': 1 if organization.public_service else 0,
            'followers': organization.metrics.get('followers', 0),
            'datasets': organization.metrics.get('datasets', 0),
            'reuses': organization.metrics.get('reuses', 0),
            'views': organization.metrics.get('views', 0),
            'extras': extras
        }
