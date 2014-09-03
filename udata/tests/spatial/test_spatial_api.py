# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.core.spatial import register_level

from udata.tests.api import APITestCase


class SpatialApiTest(APITestCase):
    def test_reference_levels(self):
        register_level('country', 'fake', 'Fake level')

        response = self.get(url_for('api.territory_levels'))
        self.assert200(response)

    def test_reference_granularities(self):
        response = self.get(url_for('api.spatial_granularities'))
        self.assert200(response)
