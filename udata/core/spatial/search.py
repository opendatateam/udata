# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.search import ModelSearchAdapter

from .models import GeoZone


__all__ = ('GeoZoneSearch', )


class GeoZoneSearch(ModelSearchAdapter):
    model = GeoZone
    fuzzy = True
    mapping = {
        'properties': {
            'zone_suggest': {
                'type': 'completion',
                'index_analyzer': 'standard',
                'search_analyzer': 'standard',
                'payloads': True,
            },
        }
    }

    @classmethod
    def serialize(cls, zone):
        return {
            'zone_suggest': {
                'input': list(set([zone.name, zone.code] + zone.keys_values)),
                'output': zone.id,
                'payload': {
                    'name': zone.name,
                    'code': zone.code,
                    'level': zone.level,
                    'keys': zone.keys,
                },
            },
        }
