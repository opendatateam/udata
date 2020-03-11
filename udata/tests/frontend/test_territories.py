from flask import url_for

from udata.tests.features.territories.test_territories_process import (
    create_geozones_fixtures
)
from udata.tests.frontend import FrontTestCase


class TerritoriesTest(FrontTestCase):
    modules = ['features.territories', 'admin', 'search', 'core.dataset',
               'core.reuse', 'core.site', 'core.organization']

    def setUp(self):
        self.paca, self.bdr, self.arles = create_geozones_fixtures()

    def test_towns(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.arles))
        self.assert404(response)  # By default towns are deactivated.

    def test_counties(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.bdr))
        self.assert404(response)  # By default counties are deactivated.

    def test_regions(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.paca))
        self.assert404(response)  # By default regions are deactivated.
