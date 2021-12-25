from elasticsearch_dsl import Date, String

from udata import search
from udata.core.site.models import current_site
from udata.i18n import lazy_gettext as _
from udata.models import Organization
from udata.search.analysis import simple
from udata.utils import to_iso_datetime


__all__ = ('OrganizationSearch', )


def max_reuses():
    return max(current_site.get_metrics()['max_org_reuses'], 10)


def max_datasets():
    return max(current_site.get_metrics()['max_org_datasets'], 10)


def max_followers():
    return max(current_site.get_metrics()['max_org_followers'], 10)


def organization_badge_labelizer(kind):
    return Organization.__badges__.get(kind, '')


@search.register
class OrganizationSearch(search.ModelSearchAdapter):
    model = Organization
    fuzzy = True

    class Meta:
        doc_type = 'Organization'

    acronym = String(index='not_analyzed')
    badges = String(index='not_analyzed')
    url = String(index='not_analyzed')
    created = Date(format='date_hour_minute_second')
    metrics = Organization.__search_metrics__

    sorts = {
        'name': 'name.raw',
        'reuses': 'metrics.reuses',
        'datasets': 'metrics.datasets',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
        'created': 'created',
        'last_modified': 'last_modified',
    }

    @classmethod
    def is_indexable(cls, org):
        return org.deleted is None

    @classmethod
    def serialize(cls, organization):
        completions = cls.completer_tokenize(organization.name)
        completions.append(organization.id)
        if organization.acronym:
            completions.append(organization.acronym)
        return {
            'name': organization.name,
            'acronym': organization.acronym,
            'description': organization.description,
            'url': organization.url,
            'metrics': organization.metrics,
            'badges': [badge.kind for badge in organization.badges],
            'created': to_iso_datetime(organization.created_at),
            'org_suggest': {
                'input': completions,
                'output': str(organization.id),
                'payload': {
                    'name': organization.name,
                    'acronym': organization.acronym,
                    'image_url': organization.logo(40, external=True),
                    'slug': organization.slug,
                },
            }
        }
