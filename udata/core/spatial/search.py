# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Territory
from udata.search import ModelSearchAdapter

__all__ = ('TerritorySearch', )


class TerritorySearch(ModelSearchAdapter):
    model = Territory
    fuzzy = True
    mapping = {
        'properties': {
            'territory_suggest': {
                'type': 'completion',
                'index_analyzer': 'standard',
                'search_analyzer': 'standard',
                'payloads': True,
            },
        }
    }

    @classmethod
    def serialize(cls, territory):
        return {
            'territory_suggest': {
                'input': list(set([territory.name, territory.code] + territory.keys.values())),
                'output': '/'.join([territory.level, territory.code, territory.name]),  # Ensure same name are duplicated
                'payload': {
                    'id': str(territory.id),
                    'name': territory.name,
                    'code': territory.code,
                    'level': territory.level,
                    'keys': territory.keys,
                },
            },
        }
