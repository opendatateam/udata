# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from elasticsearch_dsl import Completion

from flask import current_app

from udata.i18n import language, _
from udata.search import ModelSearchAdapter, register
from udata.search.analysis import standard

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


@register
class GeoZoneSearch(ModelSearchAdapter):
    model = GeoZone
    fuzzy = True
    exclude_fields = ['geom']

    class Meta:
        doc_type = 'GeoZone'

    zone_suggest = Completion(analyzer=standard,
                              search_analyzer=standard,
                              payloads=True)

    @classmethod
    def compute_weight(cls, population):
        """Weight must be in the interval [0..2147483647]"""
        if 0 <= population <= 2147483647:
            return population
        else:
            if population < 0:  # country/eh population is -99.
                return 0
            else:  # World population is 6772425850.
                return 2147483647

    @classmethod
    def is_indexable(cls, zone):
        return zone.level not in ('fr/iris', 'fr/canton', 'fr/district')

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
                'weight': cls.compute_weight(zone.population),
            },
        }
