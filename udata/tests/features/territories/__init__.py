from udata.core.spatial.factories import GeoZoneFactory
from udata.core.spatial.geoids import END_OF_TIME
from udata.settings import Testing


def create_geozones_fixtures():
    paca = GeoZoneFactory(
        id='fr:region:93@1970-01-09', level='fr:region',
        name='Provence Alpes Côtes dAzur', code='93',
        validity__start='1970-01-09', validity__end=END_OF_TIME)
    bdr = GeoZoneFactory(
        id='fr:departement:13@1860-07-01', level='fr:departement',
        parents=[paca.id], name='Bouches-du-Rhône', code='13',
        population=1993177, area=0,
        validity__start='1860-07-01', validity__end=END_OF_TIME)
    arles = GeoZoneFactory(
        id='fr:commune:13004@1942-01-01', level='fr:commune', parents=[bdr.id],
        name='Arles', code='13004', keys={'postal': '13200'},
        population=52439, area=0,
        validity__start='1942-01-01', validity__end=END_OF_TIME)
    return paca, bdr, arles


def create_old_new_regions_fixtures():
    lr = GeoZoneFactory(
        id='fr:region:91@1970-01-09', level='fr:region',
        name='Languedoc-Rousillon', code='91',
        validity__start='1956-01-01', validity__end='2015-12-31',
        population=2700266)
    occitanie = GeoZoneFactory(
        id='fr:region:76@2016-01-01', level='fr:region',
        name='Languedoc-Rousillon et Midi-Pyrénées',
        ancestors=['fr:region:91@1970-01-09'], code='76',
        validity__start='2016-01-01', validity__end=END_OF_TIME,
        population=5573000)
    return lr, occitanie


class TerritoriesSettings(Testing):
    ACTIVATE_TERRITORIES = True
    HANDLED_LEVELS = ('fr:commune', 'fr:departement', 'fr:region', 'country')
