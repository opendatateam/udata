# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from bson import ObjectId
from flask import url_for

from udata.core.spatial import register_level
from udata.utils import get_by

from udata.tests.factories import TerritoryFactory, VisibleDatasetFactory, SpatialCoverageFactory
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
