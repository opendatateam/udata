# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.core.spatial.factories import GeoZoneFactory
from udata.tests.frontend import FrontTestCase


class TerritoriesTest(FrontTestCase):

    def test_towns(self):
        arles = GeoZoneFactory(
            id='fr/commune/13004', level='fr/commune',
            name='Arles', code='13004', population=52439)
        response = self.client.get(
            url_for('territories.territory', territory=arles))
        self.assert404(response)  # By default towns are deactivated.

    def test_counties(self):
        aveyron = GeoZoneFactory(
            id='fr/departement/12', level='fr/departement', name='Aveyron',
            code='12')
        response = self.client.get(
            url_for('territories.territory', territory=aveyron))
        self.assert404(response)  # By default counties are deactivated.

    def test_regions(self):
        paca = GeoZoneFactory(
            id='fr/region/93', level='fr/region',
            name='Provence Alpes Côtes dAzur')
        response = self.client.get(
            url_for('territories.territory', territory=paca))
        self.assert404(response)  # By default regions are deactivated.
