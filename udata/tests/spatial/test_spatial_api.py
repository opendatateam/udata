# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bson import ObjectId
from flask import url_for

from udata.core.spatial import register_level
from udata.utils import get_by

from udata.tests.factories import faker, TerritoryFactory, VisibleDatasetFactory, SpatialCoverageFactory
from udata.tests.api import APITestCase


class SpatialApiTest(APITestCase):
    def test_reference_levels(self):
        register_level('country', 'fake', 'Fake level')

        response = self.get(url_for('api.territory_levels'))
        self.assert200(response)

    def test_reference_granularities(self):
        response = self.get(url_for('api.spatial_granularities'))
        self.assert200(response)

    def test_coverage_empty(self):
        response = self.get(url_for('api.spatial_coverage', level='world'))
        self.assert200(response)
        self.assertEqual(response.json, {
            'type': 'FeatureCollection',
            'features': [],
        })

    def test_coverage_for_level(self):
        register_level('country', 'included', 'Included level')
        included = [TerritoryFactory(level='included') for _ in range(2)]
        excluded = [TerritoryFactory(level='country') for _ in range(2)]
        [VisibleDatasetFactory(spatial=SpatialCoverageFactory(territories=[t.reference()])) for t in included]
        [VisibleDatasetFactory(spatial=SpatialCoverageFactory(territories=[t.reference()])) for t in excluded]

        response = self.get(url_for('api.spatial_coverage', level='included'))
        self.assert200(response)
        self.assertEqual(len(response.json['features']), 2)

        for feature in response.json['features']:
            self.assertEqual(feature['type'], 'Feature')

            territory = get_by(included, 'id', ObjectId(feature['id']))
            self.assertIsNotNone(territory)
            self.assertEqual(feature['geometry'], territory.geom)

            properties = feature['properties']
            self.assertEqual(properties['name'], territory.name)
            self.assertEqual(properties['code'], territory.code)
            self.assertEqual(properties['level'], 'included')
            self.assertEqual(properties['datasets'], 1)

    def test_suggest_territory_on_name(self):
        '''It should suggest territory based on its name'''
        with self.autoindex():
            for i in range(4):
                TerritoryFactory(name='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_territories'), qs={'q': 'test', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('code', suggestion)
            self.assertIn('level', suggestion)
            self.assertIn('keys', suggestion)
            self.assertIsInstance(suggestion['keys'], dict)
            self.assertTrue(suggestion['name'].startswith('test'))

    def test_suggest_territory_on_code(self):
        '''It should suggest territory based on its code'''
        with self.autoindex():
            for i in range(4):
                TerritoryFactory(code='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_territories'), qs={'q': 'test', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('code', suggestion)
            self.assertIn('level', suggestion)
            self.assertIn('keys', suggestion)
            self.assertIsInstance(suggestion['keys'], dict)
            self.assertTrue(suggestion['code'].startswith('test'))

    def test_suggest_territory_on_extra_key(self):
        '''It should suggest territory based on any key'''
        with self.autoindex():
            for i in range(4):
                TerritoryFactory(
                    name='in' if i % 2 else 'not-in',
                    keys={str(i): 'test-{0}'.format(i) if i % 2 else faker.word()}
                )

        response = self.get(url_for('api.suggest_territories'), qs={'q': 'test', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('code', suggestion)
            self.assertIn('level', suggestion)
            self.assertIn('keys', suggestion)
            self.assertIsInstance(suggestion['keys'], dict)
            self.assertEqual(suggestion['name'], 'in')

    def test_suggest_territory_no_match(self):
        '''It should not provide reuse suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                TerritoryFactory(name=5 * '{0}'.format(i), code=3 * '{0}'.format(i))

        response = self.get(url_for('api.suggest_territories'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_territory_empty(self):
        '''It should not provide reuse suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_territories'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)
