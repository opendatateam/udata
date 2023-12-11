import json

from datetime import timedelta

from werkzeug.datastructures import MultiDict

from udata.forms import Form
from udata.models import db
from udata.tests import TestCase
from udata.tests.helpers import assert_json_equal
from udata.utils import faker

from ..factories import GeoZoneFactory
from ..forms import SpatialCoverageField
from ..models import SpatialCoverage


A_YEAR = timedelta(days=365)


class SpatialCoverageFieldTest(TestCase):
    def factory(self):
        class Fake(db.Document):
            spatial = db.EmbeddedDocumentField(SpatialCoverage)

        class FakeForm(Form):
            spatial = SpatialCoverageField()

        return Fake, FakeForm

    def test_empty_data(self):
        Fake, FakeForm = self.factory()

        form = FakeForm()
        self.assertEqual(form.spatial.zones._value(), '')
        self.assertEqual(form.spatial.zones.data, [])
        self.assertEqual(form.spatial.granularity.data, 'other')
        self.assertIsNone(form.spatial.geom.data)

        self.assertIsNone(form.spatial.data)

        fake = Fake()
        form.populate_obj(fake)
        self.assertIsNone(fake.spatial)

    def test_initial_geom(self):
        Fake, FakeForm = self.factory()
        geom = faker.multipolygon()

        fake = Fake(spatial=SpatialCoverage(geom=geom))
        form = FakeForm(None, obj=fake)
        self.assertEqual(form.spatial.geom.data, geom)

    def test_initial_zones(self):
        Fake, FakeForm = self.factory()
        zones = [GeoZoneFactory() for _ in range(3)]

        fake = Fake(spatial=SpatialCoverage(zones=zones))
        form = FakeForm(None, obj=fake)
        self.assertEqual(
            form.spatial.zones._value(), ','.join([z.id for z in zones]))

    def test_with_zone_empty_string(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        form = FakeForm(MultiDict({
            'spatial-zones': '',
            'spatial-granularity': faker.spatial_granularity()
        }))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.zones), 0)

    def test_with_valid_zone(self):
        Fake, FakeForm = self.factory()
        zone = GeoZoneFactory()

        fake = Fake()
        form = FakeForm(MultiDict({
            'spatial-zones': zone.id,
            'spatial-granularity': faker.spatial_granularity()
        }))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.zones), 1)
        self.assertEqual(fake.spatial.zones[0], zone)

    def test_with_valid_zone_from_json(self):
        Fake, FakeForm = self.factory()
        zone = GeoZoneFactory()

        fake = Fake()
        form = FakeForm.from_json({
            'spatial': {
                'zones': zone.id,
                'granularity': faker.spatial_granularity()
            }
        })

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.zones), 1)
        self.assertEqual(fake.spatial.zones[0], zone)

    def test_with_valid_zone_ids(self):
        Fake, FakeForm = self.factory()
        zones = [GeoZoneFactory() for _ in range(3)]

        fake = Fake()
        form = FakeForm(MultiDict({
            'spatial-zones': ','.join([z.id for z in zones]),
            'spatial-granularity': faker.spatial_granularity()
        }))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.zones), len(zones))
        expected_zones = dict((z.id, z) for z in zones)
        for zone in fake.spatial.zones:
            self.assertIn(zone.id, expected_zones)
            self.assertEqual(zone, expected_zones[zone.id])

    def test_with_valid_zone_ids_from_json(self):
        Fake, FakeForm = self.factory()
        zones = [GeoZoneFactory() for _ in range(3)]

        fake = Fake()
        form = FakeForm.from_json({
            'spatial': {
                'zones': ','.join([z.id for z in zones]),
                'granularity': faker.spatial_granularity()
            }
        })

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.zones), len(zones))
        expected_zones = dict((z.id, z) for z in zones)
        for zone in fake.spatial.zones:
            self.assertIn(zone.id, expected_zones)
            self.assertEqual(zone, expected_zones[zone.id])

    def test_with_valid_geom(self):
        Fake, FakeForm = self.factory()
        geom = faker.multipolygon()

        fake = Fake()
        form = FakeForm(MultiDict({'spatial-geom': json.dumps(geom)}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        assert_json_equal(fake.spatial.geom, geom)

    def test_with_valid_geom_from_json(self):
        Fake, FakeForm = self.factory()
        geom = faker.multipolygon()

        fake = Fake()
        form = FakeForm.from_json({'spatial': {'geom': geom}})

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        assert_json_equal(fake.spatial.geom, geom)

    def test_with_invalid_geom_from_json(self):
        Fake, FakeForm = self.factory()
        geom = {'type': 'InvalidGeoJSON', 'coordinates': []}

        form = FakeForm.from_json({
            'spatial': {
                'geom': geom,
            }
        })

        form.validate()
        self.assertIn('spatial', form.errors)
        self.assertEqual(len(form.errors['spatial']), 1)

        self.assertIn('geom', form.errors['spatial'])
        self.assertEqual(len(form.errors['spatial']['geom']), 1)

    def test_with_invalid_data(self):
        Fake, FakeForm = self.factory()

        form = FakeForm(MultiDict({
            'spatial-zones': 'wrong-data', 'spatial-granularity': 'wrong'}))

        form.validate()
        self.assertIn('spatial', form.errors)
        self.assertEqual(len(form.errors['spatial']), 2)

        self.assertIn('granularity', form.errors['spatial'])
        self.assertEqual(len(form.errors['spatial']['granularity']), 1)
        self.assertIn('zones', form.errors['spatial'])
        self.assertEqual(len(form.errors['spatial']['zones']), 1)

    def test_with_initial_zones(self):
        Fake, FakeForm = self.factory()
        zones = [GeoZoneFactory() for _ in range(3)]

        fake = Fake(spatial=SpatialCoverage(zones=zones))

        zone = GeoZoneFactory()
        data = MultiDict({'spatial-zones': zone.id})

        form = FakeForm(data, obj=fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.zones), 1)
        self.assertEqual(fake.spatial.zones[0], zone)

    def test_with_initial_granularity(self):
        Fake, FakeForm = self.factory()

        fake = Fake(spatial=SpatialCoverage(
            granularity=faker.spatial_granularity()
        ))

        granularity = faker.spatial_granularity()

        data = MultiDict({'spatial-granularity': granularity})

        form = FakeForm(data, obj=fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.spatial.granularity, granularity)

    def test_with_initial_geom(self):
        Fake, FakeForm = self.factory()
        geom = faker.multipolygon()

        fake = Fake(spatial=SpatialCoverage(geom=geom))

        data = {'spatial': {'geom': geom}}

        form = FakeForm.from_json(data, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        assert_json_equal(fake.spatial.geom, geom)

    def test_with_initial_none(self):
        Fake, FakeForm = self.factory()
        zone = GeoZoneFactory()

        fake = Fake(spatial=None)
        form = FakeForm(MultiDict({
            'spatial-zones': str(zone.id),
            'spatial-granularity': faker.spatial_granularity()
        }), obj=fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.zones), 1)
        self.assertEqual(fake.spatial.zones[0], zone)

    def test_resolve_zones_from_json(self):
        Fake, FakeForm = self.factory()
        zone = GeoZoneFactory()

        zone = GeoZoneFactory()
        for i in range(3):
            GeoZoneFactory(code=zone.code)

        geoid = '{0.level}:{0.code}'.format(zone)

        fake = Fake()
        form = FakeForm.from_json({
            'spatial': {
                'zones': [geoid],
                'granularity': faker.spatial_granularity()
            }
        })

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.zones), 1)
        self.assertEqual(fake.spatial.zones[0], zone)

    def test_resolve_zones_from_json_failure(self):
        Fake, FakeForm = self.factory()
        GeoZoneFactory.create_batch(3)
        form = FakeForm.from_json({
            'spatial': {
                'zones': [
                    '{0}:{0}@{0}'.format(faker.unique_string())
                    for _ in range(2)
                ],
                'granularity': faker.spatial_granularity()
            }
        })

        form.validate()

        self.assertIn('spatial', form.errors)
        self.assertEqual(len(form.errors['spatial']), 1)

        self.assertIn('zones', form.errors['spatial'])
        self.assertEqual(len(form.errors['spatial']['zones']), 1)
