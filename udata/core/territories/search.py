# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.models import Territory
from udata.search import ModelSearchAdapter, i18n_analyzer, metrics_mapping
from udata.search.fields import Sort, BoolFacet, TemporalCoverageFacet, ExtrasFacet
from udata.search.fields import TermFacet, ModelTermFacet, RangeFacet
from udata.search.fields import BoolBooster, GaussDecay

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
