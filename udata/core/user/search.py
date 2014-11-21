# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import User, Organization
from udata.search import ModelSearchAdapter, i18n_analyzer, metrics_mapping
from udata.search.fields import Sort, ModelTermFacet, RangeFacet
from udata.search.fields import GaussDecay

# Metrics are required for user search
from . import metrics  # noqa

__all__ = ('UserSearch', )


class UserSearch(ModelSearchAdapter):
    model = User
    fuzzy = True
    # analyzer = 'not_analyzed'

    mapping = {
        'properties': {
            'first_name': {'type': 'string'},
            'last_name': {'type': 'string'},
            'about': {'type': 'string', 'analyzer': i18n_analyzer},
            'organizations': {'type': 'string', 'index_name': 'organization'},
            'visible': {'type': 'boolean'},
            'metrics': metrics_mapping(User),
            'created': {'type': 'date', 'format': 'date_hour_minute_second'},
            'user_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': True,
            },
        }
    }

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
                'input': cls.completer_tokenizer(user.full_name),
                'payload': {
                    'id': str(user.id),
                    'avatar_url': user.avatar(40),
                    'fullname': user.fullname,
                    'slug': user.slug,
                },
            },
            'visible': user.visible
        }
