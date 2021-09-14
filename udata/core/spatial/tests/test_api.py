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
        assert_json_equal(feature['geometry'], zone.geom)
        self.assertEqual(feature['id'], zone.id)

        properties = feature['properties']
        self.assertEqual(properties['name'], zone.name)
        self.assertEqual(properties['code'], zone.code)
        self.assertEqual(properties['level'], zone.level)
        self.assertEqual(properties['parents'], zone.parents)
        self.assertEqual(properties['population'], zone.population)
        self.assertEqual(properties['area'], zone.area)
        self.assertEqual(properties['keys'], zone.keys)
        self.assertEqual(properties['logo'], zone.logo_url(external=True))

    def test_zones_api_no_geom(self):
        zone = GeoZoneFactory(geom=None)

        url = url_for('api.zones', ids=[zone.id])
        response = self.get(url)
        self.assert200(response)

        self.assertEqual(len(response.json['features']), 1)

        feature = response.json['features'][0]
        self.assertEqual(feature['type'], 'Feature')
        assert_json_equal(feature['geometry'], {
            'type': 'MultiPolygon',
            'coordinates': [],
        })
        self.assertEqual(feature['id'], zone.id)

        properties = feature['properties']
        self.assertEqual(properties['name'], zone.name)
        self.assertEqual(properties['code'], zone.code)
        self.assertEqual(properties['level'], zone.level)
        self.assertEqual(properties['parents'], zone.parents)
        self.assertEqual(properties['population'], zone.population)
        self.assertEqual(properties['area'], zone.area)
        self.assertEqual(properties['keys'], zone.keys)
        self.assertEqual(properties['logo'], zone.logo_url(external=True))

    def test_zones_api_many(self):
        zones = [GeoZoneFactory() for _ in range(3)]

        url = url_for('api.zones', ids=zones)
        response = self.get(url)
        self.assert200(response)

        self.assertEqual(len(response.json['features']), len(zones))

        for zone, feature in zip(zones, response.json['features']):
            self.assertEqual(feature['type'], 'Feature')
            assert_json_equal(feature['geometry'], zone.geom)
            self.assertEqual(feature['id'], zone.id)

            properties = feature['properties']
            self.assertEqual(properties['name'], zone.name)
            self.assertEqual(properties['code'], zone.code)
            self.assertEqual(properties['level'], zone.level)
            self.assertEqual(properties['parents'], zone.parents)
            self.assertEqual(properties['population'], zone.population)
            self.assertEqual(properties['area'], zone.area)
            self.assertEqual(properties['keys'], zone.keys)
            self.assertEqual(properties['logo'], zone.logo_url(external=True))

    def test_suggest_zones_on_name(self):
        '''It should suggest zones based on its name'''
        with self.autoindex():
            for i in range(4):
                GeoZoneFactory(name='test-{0}'.format(i)
                               if i % 2 else faker.word(),
                               is_current=True)

        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'test', 'size': '5'})
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

    def test_suggest_zones_on_code(self):
        '''It should suggest zones based on its code'''
        with self.autoindex():
            for i in range(4):
                GeoZoneFactory(code='test-{0}'.format(i)
                               if i % 2 else faker.word(),
                               is_current=True)

        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'test', 'size': '5'})
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

    def test_suggest_zones_on_extra_key(self):
        '''It should suggest zones based on any key'''
        with self.autoindex():
            for i in range(4):
                GeoZoneFactory(
                    name='in' if i % 2 else 'not-in',
                    keys={str(i): 'test-{0}'.format(i)
                                  if i % 2 else faker.word()},
                    is_current=True
                )

        response = self.get(url_for('api.suggest_zones'),
                            qs={'q': 'test', 'size': '5'})
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

    def test_suggest_zones_on_extra_list_key(self):
        '''It should suggest zones based on any list key'''
        with self.autoindex():
            for i in range(4):
                GeoZoneFactory(
                    name='in' if i % 2 else 'not-in',
                    keys={str(i): ['test-{0}'.format(i)
                                   if i % 2 else faker.word()]},
                    is_current=True
                )

        response = self.get(url_for('api.suggest_zones'),
                            qs={'q': 'test', 'size': '5'})
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

    def test_suggest_zones_no_match(self):
        '''It should not provide zones suggestions if no match'''
        with self.autoindex():
            for i in range(3):
                GeoZoneFactory(name=5 * '{0}'.format(i),
                               code=3 * '{0}'.format(i),
                               is_current=True)

        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_zones_unicode(self):
        '''It should suggest zones based on its name'''
        with self.autoindex():
            for i in range(4):
                GeoZoneFactory(name='testé-{0}'.format(i)
                               if i % 2 else faker.word(),
                               is_current=True)

        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'testé', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('code', suggestion)
            self.assertIn('level', suggestion)
            self.assertIn('keys', suggestion)
            self.assertIsInstance(suggestion['keys'], dict)
            self.assertTrue(suggestion['name'].startswith('testé'))

    def test_suggest_zones_empty(self):
        '''It should not provide zones suggestion if no data is present'''
        self.init_search()
        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_only_suggest_current_zones(self):
        '''It should only suggest current zones'''
        with self.autoindex():
            for i in range(4):
                GeoZoneFactory(name='test-{0}-{1}'.format(i, 'current' if i % 2 else 'legacy'),
                               is_current=i % 2)

        response = self.get(
            url_for('api.suggest_zones'), qs={'q': 'test', 'size': '5'})
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('code', suggestion)
            self.assertIn('level', suggestion)
            self.assertIn('keys', suggestion)
            self.assertIsInstance(suggestion['keys'], dict)
            self.assertTrue(suggestion['name'].endswith('-current'))

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
        with self.autoindex():
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
        with self.autoindex():
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
        with self.autoindex():
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
        with self.autoindex():
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

    def test_coverage_for_level(self):
        GeoLevelFactory(id='top')
        GeoLevelFactory(id='sub', parents=['top'])
        GeoLevelFactory(id='child', parents=['sub'])

        topzones, subzones, childzones = [], [], []
        for _ in range(2):
            zone = GeoZoneFactory(level='top')
            topzones.append(zone)
            for _ in range(2):
                subzone = GeoZoneFactory(level='sub', parents=[zone.id])
                subzones.append(subzone)
                for _ in range(2):
                    childzone = GeoZoneFactory(
                        level='child', parents=[zone.id, subzone.id])
                    childzones.append(childzone)

        for zone in topzones + subzones + childzones:
            VisibleDatasetFactory(
                spatial=SpatialCoverageFactory(zones=[zone.id]))

        response = self.get(url_for('api.spatial_coverage', level='sub'))
        self.assert200(response)
        self.assertEqual(len(response.json['features']), len(subzones))

        for feature in response.json['features']:
            self.assertEqual(feature['type'], 'Feature')

            zone = get_by(subzones, 'id', feature['id'])
            self.assertIsNotNone(zone)
            assert_json_equal(feature['geometry'], zone.geom)

            properties = feature['properties']
            self.assertEqual(properties['name'], zone.name)
            self.assertEqual(properties['code'], zone.code)
            self.assertEqual(properties['level'], 'sub')
            # Nested levels datasets should be counted
            self.assertEqual(properties['datasets'], 3)

    def test_zone_children(self):
        paca, bdr, arles = create_geozones_fixtures()

        response = self.get(url_for('api.zone_children', id=paca.id))
        self.assertStatus(response, 501)
        response = self.get(url_for('api.zone_children', id=bdr.id))
        self.assertStatus(response, 501)
        response = self.get(url_for('api.zone_children', id=arles.id))
        self.assertStatus(response, 501)


class SpatialTerritoriesApiTest(APITestCase):
    modules = []
    settings = TerritoriesSettings

    def test_zone_datasets_with_dynamic_and_setting(self):
        paca, bdr, arles = create_geozones_fixtures()
        with self.autoindex():
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
        with self.autoindex():
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
