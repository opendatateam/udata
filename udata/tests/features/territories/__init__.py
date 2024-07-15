from udata.core.spatial.factories import GeoZoneFactory
from udata.settings import Testing


def create_geozones_fixtures():
    paca = GeoZoneFactory(
        id='fr:region:93', level='fr:region',
        name='Provence Alpes Côtes dAzur', code='93')
    bdr = GeoZoneFactory(
        id='fr:departement:13', level='fr:departement',
        name='Bouches-du-Rhône', code='13')
    arles = GeoZoneFactory(
        id='fr:commune:13004', level='fr:commune',
        name='Arles', code='13004')
    return paca, bdr, arles


def create_old_new_regions_fixtures():
    lr = GeoZoneFactory(
        id='fr:region:91', level='fr:region',
        name='Languedoc-Rousillon', code='91')
    occitanie = GeoZoneFactory(
        id='fr:region:76', level='fr:region',
        name='Languedoc-Rousillon et Midi-Pyrénées', code='76')
    return lr, occitanie


class TerritoriesSettings(Testing):
    ACTIVATE_TERRITORIES = True
    HANDLED_LEVELS = ('fr:commune', 'fr:departement', 'fr:region', 'country')
