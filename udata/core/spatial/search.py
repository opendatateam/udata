# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app

from udata.i18n import language, _
from udata.search import ModelSearchAdapter

from .models import GeoZone


__all__ = ('GeoZoneSearch', )


def labels_for_zone(zone):
    '''
    Extract all known zone labels
    - main code
    - keys (postal...)
    - name translation in every supported languages
    '''
    labels = set([zone.name, zone.code] + zone.keys_values)
    for lang in current_app.config['LANGUAGES'].keys():
        with language(lang):
            labels.add(_(zone.name))
    return list(labels)


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
                'input': labels_for_zone(zone),
                'output': zone.id,
                'payload': {
                    'name': zone.name,
                    'code': zone.code,
                    'level': zone.level,
                    'keys': zone.keys,
                },
            },
        }
