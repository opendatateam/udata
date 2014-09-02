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
                'index_analyzer': 'simple',
                'search_analyzer': 'simple',
                'payloads': True,
            },
        }
    }

    @classmethod
    def serialize(cls, territory):
        return {
            'territory_suggest': {
                'input': list(set([territory.name, territory.code] + territory.keys.values())),
                'payload': {
                    'id': str(territory.id),
                    'name': territory.name,
                    'code': territory.code,
                },
            },
        }
