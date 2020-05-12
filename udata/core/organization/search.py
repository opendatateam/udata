from elasticsearch_dsl import Completion, Date, String

from udata import search
from udata.core.site.models import current_site
from udata.i18n import lazy_gettext as _
from udata.models import Organization
from udata.search.analysis import simple
from udata.search.fields import TermsFacet, RangeFacet
from udata.utils import to_iso_datetime


__all__ = ('OrganizationSearch', )
lazy = search.lazy_config('organization')


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

    name = String(analyzer=search.i18n_analyzer, fields={
        'raw': String(index='not_analyzed')
    })
    acronym = String(index='not_analyzed')
    description = String(analyzer=search.i18n_analyzer)
    badges = String(index='not_analyzed')
    url = String(index='not_analyzed')
    created = Date(format='date_hour_minute_second')
    metrics = Organization.__search_metrics__
    org_suggest = Completion(analyzer=simple,
                             search_analyzer=simple,
                             payloads=True)

    sorts = {
        'name': 'name.raw',
        'reuses': 'metrics.reuses',
        'datasets': 'metrics.datasets',
        'followers': 'metrics.followers',
        'views': 'metrics.views',
        'created': 'created',
        'last_modified': 'last_modified',
    }
    facets = {
        'reuses': RangeFacet(field='metrics.reuses',
                             ranges=[('none', (None, 1)),
                                     ('few', (1, 5)),
                                     ('many', (5, None))],
                             labels={
                                'none': _('No reuses'),
                                'few': _('Few reuses'),
                                'many': _('Many reuses'),
                             }),
        'badge': TermsFacet(field='badges',
                            labelizer=organization_badge_labelizer),
        'datasets': RangeFacet(field='metrics.datasets',
                               ranges=[('none', (None, 1)),
                                       ('few', (1, 5)),
                                       ('many', (5, None))],
                               labels={
                                    'none': _('No datasets'),
                                    'few': _('Few datasets'),
                                    'many': _('Many datasets'),
                               }),
        'followers': RangeFacet(field='metrics.followers',
                                ranges=[('none', (None, 1)),
                                        ('few', (1, 5)),
                                        ('many', (5, None))],
                                labels={
                                     'none': _('No followers'),
                                     'few': _('Few followers'),
                                     'many': _('Many followers'),
                                }),
    }
    boosters = [
        search.GaussDecay('metrics.followers', max_followers, decay=lazy('followers_decay')),
        search.GaussDecay('metrics.reuses', max_reuses, decay=lazy('reuses_decay')),
        search.GaussDecay('metrics.datasets', max_datasets, decay=lazy('datasets_decay')),
    ]

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
