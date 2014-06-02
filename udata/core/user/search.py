# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import User
from udata.search import ModelSearchAdapter, Sort, i18n_analyzer

__all__ = ('UserSearch', )


class UserSearch(ModelSearchAdapter):
    model = User
    mapping = {
        'properties': {
            'user_suggest': {
                'type': 'completion',
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': True,
            },
        }
    }

    @classmethod
    def serialize(cls, user):
        return {
            'user_suggest': {
                'input': [user.first_name, user.last_name],
                'payload': {
                    'id': str(user.id),
                    'avatar_url': user.avatar_url,
                    'fullname': user.fullname,
                    'slug': user.slug,
                },
            },
        }
