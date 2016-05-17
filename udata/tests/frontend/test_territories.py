# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.core.spatial.factories import GeoZoneFactory
from udata.tests.frontend import FrontTestCase


class TerritoriesTest(FrontTestCase):

    def test_towns(self):
        arles = GeoZoneFactory(
            id='fr/town/13004', level='fr/town',
            name='Arles', code='13004', population=52439)
        response = self.client.get(
            url_for('territories.town', territory=arles))
        self.assert404(response)  # By default towns are deactivated.

    def test_counties(self):
        aveyron = GeoZoneFactory(
            id='fr/county/12', level='fr/county', name='Aveyron', code='12')
        response = self.client.get(
            url_for('territories.county', territory=aveyron))
        self.assert404(response)  # By default counties are deactivated.
