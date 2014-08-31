# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.core.territories import register_level_tree, register_level
from udata.core.territories.commands import territory_extractor, register_aggregate
from udata.i18n import lazy_gettext as _

register_level_tree('country', (
    ('fr-region', _('French region')),
    ('fr-county', _('French county')),
    ('fr-district', _('Arrondissement')),
    ('fr-town', _('French town')),
))

register_level('fr-county', 'fr-epci', 'EPCI')

# Cities with districts
register_aggregate('fr-town', '75056', 'Paris', [('fr-county', '75')])

register_aggregate('fr-town', '13055', 'Marseille', [
    ('fr-town', '132{0:0>2}'.format(i)) for i in range(1, 17)
])

register_aggregate('fr-town', '69123', 'Lyon', [
    ('fr-town', '6938{0}'.format(i)) for i in range(1, 9)
])


# Overseas territories as counties
register_aggregate('fr-county', '975', 'Saint-Piere-et-Miquelon', [('country', 'pm')])
register_aggregate('fr-county', '977', 'Saint-Barthélemy', [('country', 'bl')])
register_aggregate('fr-county', '978', 'Saint-Martin', [('country', 'mf')])
register_aggregate('fr-county', '986', 'Wallis-et-Futuna', [('country', 'wf')])
register_aggregate('fr-county', '987', 'Polynésie française', [('country', 'pf')])
register_aggregate('fr-county', '988', 'Nouvelle-Calédonie', [('country', 'nc')])
register_aggregate('fr-county', '984', 'Terres australes et antarctiques françaises', [('country', 'tf')])

# Country groups and subsets
register_aggregate('country-group', 'ue', 'Union Européenne', [
    ('country', code) for code in
    ('at', 'be', 'bg', 'cy', 'hr', 'dk', 'ee', 'fi', 'gr', 'fr', 'es', 'de', 'hu', 'ie',
        'it', 'lv', 'lt', 'lu', 'mt', 'nl', 'pl', 'pt', 'cz', 'ro', 'gb', 'sk', 'si', 'se')
])

register_aggregate('country-subset', 'fr-metro', 'France métropolitaine', [
    ('fr-county', code) for code in
    (['{0:0>2}'.format(i) for i in range(1, 20)]
        + ['2a', '2b']
        + ['{0:0>2}'.format(i) for i in range(21, 96)])
])

register_aggregate('country-subset', 'fr-dom', 'DOM', [
    ('fr-county', code) for code in '971', '972', '973', '974', '976'
])

register_aggregate('country-subset', 'fr-domtom', 'France d\'outre-mer', [
    ('fr-county', code) for code in '971', '972', '973', '974', '975', '976', '977', '978', '984', '986', '987', '988'
])



@territory_extractor('fr-district', r'^arrondissements-')
def extract_french_district(polygon):
    '''
    Extract a french district informations from a MultiPolygon.
    Based on data from http://www.data.gouv.fr/datasets/contours-des-arrondissements-francais-issus-d-openstreetmap/
    '''
    props = polygon['properties']
    code = props['insee_ar'].lower()
    name = props['nom']
    keys = {
        'insee': code,
    }
    return code, name, keys


@territory_extractor('fr-epci', r'^epci-')
def extract_french_epci(polygon):
    '''
    Extract a french EPCI informations from a MultiPolygon.
    Based on data from http://www.data.gouv.fr/datasets/contours-des-epci-2014/
    '''
    props = polygon['properties']
    code = props['siren_epci'].lower()
    name = props.get('nom_osm') or props['nom_epci']
    keys = {
        'siren': props['siren_epci'],
        'ptot': props['ptot_epci'],
        'osm': props['osm_id'],
        'type_epci': props['type_epci']
    }
    return code, name.decode('cp1252'), keys


@territory_extractor('fr-county', r'^departements-')
def extract_french_county(polygon):
    '''
    Extract a french country informations from a MultiPolygon.
    Based on data from http://www.data.gouv.fr/datasets/contours-des-departements-francais-issus-d-openstreetmap/
    '''
    props = polygon['properties']
    code = props['code_insee'].lower()
    name = props['nom']
    keys = {
        'insee': code,
        'nuts3': props['nuts3'],
    }
    return code, name.decode('cp1252'), keys


@territory_extractor('fr-region', r'^regions-')
def extract_french_region(polygon):
    '''
    Extract a french region informations from a MultiPolygon.
    Based on data from http://www.data.gouv.fr/datasets/contours-des-regions-francaises-sur-openstreetmap/
    '''
    props = polygon['properties']
    code = props['code_insee'].lower()
    name = props['nom']
    keys = {
        'insee': code,
        'nuts2': props['nuts2'],
        'iso3166_2': props['iso3166_2'],
    }
    return code, name, keys


@territory_extractor('fr-town', r'^communes-')
def extract_french_town(polygon):
    '''
    Extract a french town informations from a MultiPolygon.
    Based on data from http://www.data.gouv.fr/datasets/decoupage-administratif-communal-francais-issu-d-openstreetmap/
    '''
    props = polygon['properties']
    code = props['insee'].lower()
    name = props['nom']
    keys = {
        'insee': code,
    }
    return code, name, keys
