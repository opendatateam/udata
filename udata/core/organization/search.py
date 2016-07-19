# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from elasticsearch_dsl import Completion, Date, Long, String

from udata import search
from udata.models import Organization
from udata.core.site.views import current_site

from . import metrics  # noqa: Metrics are need for the mapping

__all__ = ('OrganizationSearch', )


def max_reuses():
    return max(current_site.metrics.get('max_org_reuses'), 10)


def max_datasets():
    return max(current_site.metrics.get('max_org_datasets'), 10)


def max_followers():
    return max(current_site.metrics.get('max_org_followers'), 10)


def organization_badge_labelizer(label, kind):
    return Organization.__badges__.get(kind, '')


class OrganizationSearch(search.ModelSearchAdapter):
    class Meta:
        doc_type = 'Organization'
        model = Organization
        fuzzy = True

    name = String(analyzer=search.i18n_analyzer, fields={
        'raw': String(index='not_analyzed')
    })
    acronym = String(index='not_analyzed')
    description = String(analyzer=search.i18n_analyzer)
    badges = String(index='not_analyzed')
    url = String()
    created = Date(format='date_hour_minute_second')
    metrics = search.metrics_mapping_for(Organization)
    org_suggest = Completion(analyzer='simple',
                             search_analyzer='simple',
                             payloads=True)

    fields = (
        'name^6',
        'acronym^6',
        'description',
    )
    sorts = {
        'name': search.Sort('name.raw'),
        'reuses': search.Sort('metrics.reuses'),
        'datasets': search.Sort('metrics.datasets'),
        'followers': search.Sort('metrics.followers'),
        'views': search.Sort('metrics.views'),
        'created': search.Sort('created'),
    }
    facets = {
        'reuses': search.RangeFacet('metrics.reuses'),
        'badge': search.TermFacet('badges',
                                  labelizer=organization_badge_labelizer),
        'permitted_reuses': search.RangeFacet('metrics.permitted_reuses'),
        'datasets': search.RangeFacet('metrics.datasets'),
        'followers': search.RangeFacet('metrics.followers'),
    }
    boosters = [
        search.GaussDecay('metrics.followers', max_followers, decay=0.8),
        search.GaussDecay('metrics.reuses', max_reuses, decay=0.9),
        search.GaussDecay('metrics.datasets', max_datasets, decay=0.9),
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
            'created': organization.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'org_suggest': {
                'input': completions,
                'output': str(organization.id),
                'payload': {
                    'name': organization.name,
                    'acronym': organization.acronym,
                    'image_url': organization.logo(40),
                    'slug': organization.slug,
                },
            }
        }
