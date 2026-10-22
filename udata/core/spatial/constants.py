from udata.i18n import L_

BASE_GRANULARITIES = [
    ("poi", L_("POI")),
    ("other", L_("Other")),
]

ADMIN_LEVEL_MIN = 1
ADMIN_LEVEL_MAX = 110

# Which levels the zones autocomplete proposes, and in which relevance order.
#
# We deliberately restrict suggestions to the levels whose metadata is actually
# well filled: communes, departments, regions and EPCI. Detail levels
# (arrondissements, cantons, IRIS) are NOT suggested at all — they are sparsely
# used and would bury the levels people actually mean.
#
# The order is NOT `admin_level`: relevance is not monotonic with granularity.
# On a French portal a commune is the most likely intent; EPCI sit below
# departments/regions; countries and country groupings (Europe, World) are the
# least useful. Lower sorts first; it only breaks ties between zones of equal
# match quality.
LEVEL_PRIORITY = {
    "fr:commune": 0,  # the city/town: ~90% of intents
    "fr:departement": 1,
    "fr:region": 2,
    "fr:epci": 3,  # metropolises / intercommunalities: below dept/region
    "fr:collectivite": 4,  # overseas collectivities are French territory
    "country": 5,  # a French platform: pays less useful
    "country-subset": 6,  # technical groupings ("métropole", "DOM")
    "country-group": 7,  # Europe / World: least useful
}
DEFAULT_LEVEL_PRIORITY = 99

# Only these levels are returned by the autocomplete (derived from the ranking
# above); everything else (arrondissements, cantons, IRIS...) is excluded.
SUGGESTABLE_LEVELS = list(LEVEL_PRIORITY)

# Levels proposed by default when the autocomplete query is empty: broad, stable
# entry points rather than "Monde" + countries alphabetically.
DEFAULT_SUGGEST_LEVELS = ["fr:region", "fr:departement"]
