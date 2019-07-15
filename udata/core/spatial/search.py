from elasticsearch_dsl import Completion

from flask import current_app

from udata.i18n import language, _
from udata.search import ModelSearchAdapter, register
from udata.search.analysis import standard

from .models import GeoZone, admin_levels, ADMIN_LEVEL_MAX


__all__ = ('GeoZoneSearch', )


PONDERATION_STEP = 10000
# Compute weight relative to 10⁸.
# Only 12 countries + UE have emore population.
# This is not significative in the ranking algorithm for countries.
# Given ES indexes weight as an integer,
# zones start to gain weight at MAX_POPULATION / PONDERATION_STEP
# Here starts at 10k inhabitants
MAX_POPULATION = 1E8


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
    def compute_weight(cls, zone):
        '''
        Give a weight to the zone according to its administrative level first
        and then its population.
        Scoring is in [0 ..  ~(ADMIN_LEVEL_MAX * (10 + 1) * PONDERATION_STEP)]
        '''
        # Each level give a step
        level = max(admin_levels.get(zone.level, ADMIN_LEVEL_MAX), 1)
        level_weight = (ADMIN_LEVEL_MAX / level) * 10 * PONDERATION_STEP
        # Population gives 0 < weight < PONDERATION_STEP
        # to rank between level steps only
        # NB: to be realy progressive, we should take the max population
        # by administrative level but it would either to much time consumption
        # or too much refactoring (storing the max population by level)
        population = min(max(0, zone.population or 0), MAX_POPULATION)
        population_weight = (population / MAX_POPULATION) * PONDERATION_STEP
        return int(level_weight + population_weight)

    @classmethod
    def is_indexable(cls, zone):
        return (
            # Only index non-excluded levels
            zone.level not in current_app.config['SPATIAL_SEARCH_EXCLUDE_LEVELS']
            # Only index latest zone
            and zone.is_current
        )

    @classmethod
    def labels_for_zone(cls, zone):
        '''
        Extract all known zone labels
        - main code
        - keys (postal...)
        - name translation in every supported languages
        '''
        labels = set(cls.completer_tokenize(zone.name))
        labels.add(zone.code)
        labels |= set(zone.keys_values)
        for lang in current_app.config['LANGUAGES'].keys():
            with language(lang):
                labels |= set(cls.completer_tokenize(_(zone.name)))
        return list(labels)

    @classmethod
    def serialize(cls, zone):
        return {
            'zone_suggest': {
                'input': cls.labels_for_zone(zone),
                'output': zone.id,
                'payload': {
                    'name': zone.name,
                    'code': zone.code,
                    'level': zone.level,
                    'keys': zone.keys,
                },
                'weight': cls.compute_weight(zone),
            },
        }
