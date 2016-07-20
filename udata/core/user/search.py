# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from elasticsearch_dsl import Completion, Date, String, Boolean

from udata.models import User, Organization
from udata.search import ModelSearchAdapter
from udata.search import i18n_analyzer, metrics_mapping_for, register
from udata.search.fields import Sort, ModelTermFacet, RangeFacet
from udata.search.fields import GaussDecay
from udata.search.analyzers import simple

# Metrics are required for user search
from . import metrics  # noqa

__all__ = ('UserSearch', )


@register
class UserSearch(ModelSearchAdapter):
    model = User
    fuzzy = True

    class Meta:
        doc_type = 'User'

    first_name = String()
    last_name = String()
    about = String(analyzer=i18n_analyzer)
    organizations = String()
    visible = Boolean()
    metrics = metrics_mapping_for(User)
    created = Date(format='date_hour_minute_second')
    user_suggest = Completion(analyzer=simple,
                              search_analyzer=simple,
                              payloads=True)

    fields = (
        'last_name^6',
        'first_name^5',
        'about'
    )
    sorts = {
        'last_name': Sort('last_name'),
        'first_name': Sort('first_name'),
        'datasets': Sort('metrics.datasets'),
        'reuses': Sort('metrics.reuses'),
        'followers': Sort('metrics.followers'),
        'views': Sort('metrics.views'),
        'created': Sort('created'),
    }
    facets = {
        'organization': ModelTermFacet('organizations', Organization),
        'reuses': RangeFacet('metrics.reuses'),
        'datasets': RangeFacet('metrics.datasets'),
    }
    boosters = [
        GaussDecay('metrics.reuses', 50, decay=0.8),
        GaussDecay('metrics.datasets', 50, decay=0.8),
        GaussDecay('metrics.followers', 200, 200, decay=0.8),
    ]

    @classmethod
    def serialize(cls, user):
        return {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'about': user.about,
            'organizations': [str(o.id) for o in user.organizations],
            'metrics': user.metrics,
            'created': user.created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'user_suggest': {
                'input': cls.completer_tokenize(user.fullname) + [user.id],
                'output': str(user.id),
                'payload': {
                    'avatar_url': user.avatar(40),
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'slug': user.slug,
                },
            },
            'visible': user.visible
        }
