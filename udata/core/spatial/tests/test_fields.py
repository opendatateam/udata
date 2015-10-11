# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from werkzeug.datastructures import MultiDict

from udata.forms import Form
from udata.models import db
from udata.tests import TestCase
from udata.tests.factories import GeoZoneFactory, random_spatial_granularity

from ..models import SpatialCoverage
from ..forms import SpatialCoverageField


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
        # self.assertEqual(form.spatial.granularity._value(), '')
        self.assertEqual(form.spatial.granularity.data, 'other')

        self.assertEqual(form.spatial.data,
                         {'zones': [], 'granularity': 'other'})

        fake = Fake()
        form.populate_obj(fake)
        self.assertIsInstance(fake.spatial, SpatialCoverage)

    def test_initial_values(self):
        Fake, FakeForm = self.factory()
        zones = [GeoZoneFactory() for _ in range(3)]

        fake = Fake(spatial=SpatialCoverage(zones=zones))
        form = FakeForm(None, fake)
        self.assertEqual(
            form.spatial.zones._value(), ','.join([z.id for z in zones]))

    def test_with_zone_empty_string(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        form = FakeForm(MultiDict({
            'spatial-zones': '',
            'spatial-granularity': random_spatial_granularity()
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
            'spatial-granularity': random_spatial_granularity()
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
                'granularity': random_spatial_granularity()
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
            'spatial-granularity': random_spatial_granularity()
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
                'granularity': random_spatial_granularity()
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

    def test_with_initial(self):
        Fake, FakeForm = self.factory()
        zones = [GeoZoneFactory() for _ in range(3)]

        fake = Fake(spatial=SpatialCoverage(
            zones=zones,
            granularity=random_spatial_granularity()
        ))

        zone = GeoZoneFactory()
        data = MultiDict({
            'spatial-zones': zone.id,
            'spatial-granularity': random_spatial_granularity()
        })

        form = FakeForm(data, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.zones), 1)
        self.assertEqual(fake.spatial.zones[0], zone)

    def test_with_initial_none(self):
        Fake, FakeForm = self.factory()
        zone = GeoZoneFactory()

        fake = Fake(spatial=None)
        form = FakeForm(MultiDict({
            'spatial-zones': str(zone.id),
            'spatial-granularity': random_spatial_granularity()
        }), fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.zones), 1)
        self.assertEqual(fake.spatial.zones[0], zone)
