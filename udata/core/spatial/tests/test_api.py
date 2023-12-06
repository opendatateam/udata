from flask import url_for

from udata.utils import get_by

from udata.utils import faker
from udata.tests.api import APITestCase
from udata.tests.features.territories import (
    create_geozones_fixtures, TerritoriesSettings
)
from udata.tests.helpers import assert_json_equal
from udata.core.organization.factories import OrganizationFactory
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.spatial.factories import (
    SpatialCoverageFactory, GeoZoneFactory, GeoLevelFactory
)


class SpatialApiTest(APITestCase):
    modules = []

    def test_zones_api_one(self):
        zone = GeoZoneFactory()

        url = url_for('api.zones', ids=[zone.id])
        response = self.get(url)
        self.assert200(response)

        self.assertEqual(len(response.json['features']), 1)

        feature = response.json['features'][0]
        self.assertEqual(feature['type'], 'Feature')
        self.assertEqual(feature['id'], zone.id)

        properties = feature['properties']
        self.assertEqual(properties['name'], zone.name)
        self.assertEqual(properties['code'], zone.code)
        self.assertEqual(properties['level'], zone.level)
        self.assertEqual(properties['uri'], zone.uri)

    def test_zones_api_many(self):
        zones = [GeoZoneFactory() for _ in range(3)]

        url = url_for('api.zones', ids=zones)
        response = self.get(url)
        self.assert200(response)

        self.assertEqual(len(response.json['features']), len(zones))

        for zone, feature in zip(zones, response.json['features']):
            self.assertEqual(feature['type'], 'Feature')
            self.assertEqual(feature['id'], zone.id)

            properties = feature['properties']
            self.assertEqual(properties['name'], zone.name)
            self.assertEqual(properties['code'], zone.code)
            self.assertEqual(properties['level'], zone.level)
            self.assertEqual(properties['uri'], zone.uri)

    def test_suggest_zones_on_name(self):
        '''It should suggest zones based on its name'''
        for i in range(4):
            GeoZoneFactory(name='name-test-{0}'.format(i)
                           if i % 2 else faker.word())

        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'name-test', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('code', suggestion)
            self.assertIn('uri', suggestion)
            self.assertIn('level', suggestion)
            self.assertIn('name-test', suggestion['name'])

    def test_suggest_zones_sorted(self):
        '''It should suggest zones based on its name'''
        country_level = GeoLevelFactory(id='country', name='country', admin_level=10)
        region_level = GeoLevelFactory(id='region', name='region', admin_level=20)
        country_zone = GeoZoneFactory(name='name-test-country', level=country_level.id)
        region_zone = GeoZoneFactory(name='name-test-region', level=region_level.id)

        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'name-test', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)
        self.assertEqual((response.json[0]['id']), country_zone.id)
        self.assertEqual((response.json[1]['id']), region_zone.id)

    def test_suggest_zones_on_code(self):
        '''It should suggest zones based on its code'''
        for i in range(4):
            GeoZoneFactory(code='code-test-{0}'.format(i)
                           if i % 2 else faker.word())

        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'code-test', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('code', suggestion)
            self.assertIn('level', suggestion)
            self.assertIn('uri', suggestion)
            self.assertIn('code-test', suggestion['code'])

    def test_suggest_zones_no_match(self):
        '''It should not provide zones suggestions if no match'''
        for i in range(3):
            GeoZoneFactory(name=5 * '{0}'.format(i),
                           code=3 * '{0}'.format(i))

        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_zones_unicode(self):
        '''It should suggest zones based on its name'''
        for i in range(4):
            GeoZoneFactory(name='name-testé-{0}'.format(i)
                           if i % 2 else faker.word())

        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'name-testé', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('code', suggestion)
            self.assertIn('level', suggestion)
            self.assertIn('uri', suggestion)
            self.assertIn('name-testé', suggestion['name'])

    def test_suggest_zones_empty(self):
        '''It should not provide zones suggestion if no data is present'''
        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_spatial_levels(self):
        levels = [GeoLevelFactory() for _ in range(3)]

        response = self.get(url_for('api.spatial_levels'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(levels))

    def test_spatial_granularities(self):
        levels = [GeoLevelFactory() for _ in range(3)]

        response = self.get(url_for('api.spatial_granularities'))
        self.assert200(response)
        self.assertEqual(len(response.json), len(levels) + 2)

    def test_zone_datasets_empty(self):
        paca, bdr, arles = create_geozones_fixtures()
        response = self.get(url_for('api.zone_datasets', id=paca.id))
        self.assert200(response)
        self.assertEqual(response.json, [])

    def test_zone_datasets(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = self.get(url_for('api.zone_datasets', id=paca.id))
        self.assert200(response)
        self.assertEqual(len(response.json), 3)

    def test_zone_datasets_with_size(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = self.get(url_for('api.zone_datasets', id=paca.id),
                            qs={'size': 2})
        self.assert200(response)
        self.assertEqual(len(response.json), 2)

    def test_zone_datasets_with_dynamic(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = self.get(
            url_for('api.zone_datasets', id=paca.id), qs={'dynamic': 1})
        self.assert200(response)
        # No dynamic datasets given that the setting is deactivated by default.
        self.assertEqual(len(response.json), 3)

    def test_zone_datasets_with_dynamic_and_size(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = self.get(
            url_for('api.zone_datasets', id=paca.id),
            qs={'dynamic': 1, 'size': 2})
        self.assert200(response)
        # No dynamic datasets given that the setting is deactivated by default.
        self.assertEqual(len(response.json), 2)

    def test_coverage_empty(self):
        GeoLevelFactory(id='top')
        response = self.get(url_for('api.spatial_coverage', level='top'))
        self.assert200(response)
        self.assertEqual(response.json, {
            'type': 'FeatureCollection',
            'features': [],
        })


class SpatialTerritoriesApiTest(APITestCase):
    modules = []
    settings = TerritoriesSettings

    def test_zone_datasets_with_dynamic_and_setting(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = self.get(
            url_for('api.zone_datasets', id=paca.id), qs={'dynamic': 1})
        self.assert200(response)
        # No dynamic datasets given that they are added by udata-front extension.
        self.assertEqual(len(response.json), 3)

    def test_zone_datasets_with_dynamic_and_setting_and_size(self):
        paca, bdr, arles = create_geozones_fixtures()
        organization = OrganizationFactory()
        for _ in range(3):
            VisibleDatasetFactory(
                organization=organization,
                spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = self.get(
            url_for('api.zone_datasets', id=paca.id), qs={
                'dynamic': 1,
                'size': 2
            })
        self.assert200(response)
        # No dynamic datasets given that they are added by udata-front extension.
        self.assertEqual(len(response.json), 2)
