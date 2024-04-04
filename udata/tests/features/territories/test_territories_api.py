from flask import url_for

from udata.core.spatial.factories import GeoZoneFactory
from udata.tests.api import APITestCase
from udata.tests.features.territories import (
    create_geozones_fixtures, create_old_new_regions_fixtures,
    TerritoriesSettings
)


class TerritoriesAPITest(APITestCase):
    modules = []
    settings = TerritoriesSettings

    def setUp(self):
        self.paca, self.bdr, self.arles = create_geozones_fixtures()

    def test_suggest_no_parameter(self):
        response = self.get(url_for('api.suggest_territory'))
        self.assert400(response)

    def test_suggest_empty(self):
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'tes'})
        self.assert200(response)
        self.assertEqual(response.json, [])
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'test'})
        self.assert200(response)
        self.assertEqual(response.json, [])

    def test_suggest_town(self):
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'arle'})
        self.assert200(response)
        result = response.json[0]
        self.assertEqual(result['title'], self.arles.name)
        self.assertEqual(result['id'], self.arles.id)
        self.assertIn('page', result)

    def test_suggest_town_five_letters(self):
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'arles'})
        self.assert200(response)
        result = response.json[0]
        self.assertEqual(result['title'], self.arles.name)
        self.assertEqual(result['id'], self.arles.id)
        self.assertIn('page', result)

    def test_suggest_town_by_insee_code(self):
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': '13004'})
        self.assert200(response)
        result = response.json[0]
        self.assertEqual(result['id'], self.arles.id)
        self.assertEqual(result['title'], self.arles.name)

    def test_suggest_towns(self):
        arles_sur_tech = GeoZoneFactory(
            id='fr:commune:66009', level='fr:commune',
            name='Arles-sur-Tech', code='66009')
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'arles'})
        self.assert200(response)
        results = response.json
        self.assertEqual(len(results), 2)
        # Arles must be first given the population.
        self.assertEqual(results[0]['id'], self.arles.id)
        self.assertEqual(results[1]['id'], arles_sur_tech.id)

    def test_suggest_county(self):
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'bouche'})
        self.assert200(response)
        result = response.json[0]
        self.assertEqual(result['title'], self.bdr.name)
        self.assertEqual(result['id'], self.bdr.id)
        self.assertIn('page', result)

    def test_suggest_region(self):
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'prov'})
        self.assert200(response)
        result = response.json[0]
        self.assertEqual(result['title'], self.paca.name)
        self.assertEqual(result['id'], self.paca.id)
        self.assertIn('page', result)

    def test_suggest_old_new_region(self):
        lr, occitanie = create_old_new_regions_fixtures()
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'langue'})
        self.assert200(response)
        self.assertEqual(len(response.json), 2)
        result = response.json[1]
        self.assertEqual(result['title'], occitanie.name)
        self.assertEqual(result['id'], occitanie.id)
        result = response.json[0]
        self.assertEqual(result['title'], lr.name)
        self.assertEqual(result['id'], lr.id)

    def test_suggest_county_by_id(self):
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': '13'})
        self.assert200(response)
        result = response.json[0]
        self.assertEqual(result['id'], self.bdr.id)
        self.assertEqual(result['title'], self.bdr.name)

    def test_suggest_town_and_county(self):
        bouchet = GeoZoneFactory(
            id='fr:commune:26054', level='fr:commune',
            name='Bouchet', code='26054')
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'bouche'})
        self.assert200(response)
        results = response.json
        self.assertEqual(len(results), 2)
        # BDR must be first given the population.
        self.assertEqual(results[0]['id'], self.bdr.id)
        self.assertEqual(results[1]['id'], bouchet.id)

    def test_suggest_drom_com(self):
        guyane = GeoZoneFactory(
            id='fr:departement:973', level='fr:departement',
            name='Guyane', code='973')
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'guya'})
        self.assert200(response)
        results = response.json
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], guyane.id)

    def test_suggest_drom_com_by_code(self):
        guyane = GeoZoneFactory(
            id='fr:departement:973', level='fr:departement',
            name='Guyane', code='973')
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': '973'})
        self.assert200(response)
        results = response.json
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], guyane.id)

    def test_suggest_corsica(self):
        bastia = GeoZoneFactory(
            id='fr:commune:2b033', level='fr:commune',
            name='Bastia', code='2b033')
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'basti'})
        self.assert200(response)
        results = response.json
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], bastia.id)

    def test_suggest_corsica_by_code(self):
        bastia = GeoZoneFactory(
            id='fr:commune:2b033', level='fr:commune',
            name='Bastia', code='2b033')
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': '2b033'})
        self.assert200(response)
        results = response.json
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], bastia.id)

    def test_suggest_corsica_by_county_code(self):
        haute_corse = GeoZoneFactory(
            id='fr:departement:2b', level='fr:departement',
            name='Haute-Corse', code='2b')
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': '2b'})
        self.assert200(response)
        results = response.json
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], haute_corse.id)

    def test_not_suggest_country(self):
        GeoZoneFactory(
            id='country:fr', level='country', name='France')
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'fra'})
        self.assert200(response)
        results = response.json
        self.assertEqual(len(results), 0)
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'fran'})
        self.assert200(response)
        results = response.json
        self.assertEqual(len(results), 0)
        response = self.get(
            url_for('api.suggest_territory'), qs={'q': 'franc'})
        self.assert200(response)
        results = response.json
        self.assertEqual(len(results), 0)

    def test_suggest_unicode(self):
        response = self.get(url_for('api.suggest_territory'),
                                    qs={'q': 'Bouches-du-Rhône'})
        self.assert200(response)
        result = response.json[0]
        self.assertEqual(result['title'], self.bdr.name)
        self.assertEqual(result['id'], self.bdr.id)
        self.assertIn('page', result)
