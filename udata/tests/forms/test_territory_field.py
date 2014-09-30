# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from shapely.geometry import shape
from shapely.ops import cascaded_union

from werkzeug.datastructures import MultiDict

from udata.forms import Form, fields
from udata.models import db, SpatialCoverage
from udata.tests import TestCase
from udata.tests.factories import TerritoryFactory

from udata.models import SPATIAL_GRANULARITIES


VALID_GRANULARITY = SPATIAL_GRANULARITIES.keys()[0]


class TerritoryFieldTest(TestCase):
    def factory(self):
        class Fake(db.Document):
            spatial = db.EmbeddedDocumentField(SpatialCoverage)

        class FakeForm(Form):
            spatial = fields.SpatialCoverageField()

        return Fake, FakeForm

    def test_empty_data(self):
        Fake, FakeForm = self.factory()

        form = FakeForm()
        self.assertEqual(form.spatial.territories._value(), '')
        self.assertEqual(form.spatial.territories.data, [])
        # self.assertEqual(form.spatial.granularity._value(), '')
        self.assertEqual(form.spatial.granularity.data, 'other')

        self.assertEqual(form.spatial.data, {'territories': [], 'granularity': 'other'})

        fake = Fake()
        form.populate_obj(fake)
        self.assertIsInstance(fake.spatial, SpatialCoverage)

    def test_initial_values(self):
        Fake, FakeForm = self.factory()
        territories = [TerritoryFactory() for _ in range(3)]

        fake = Fake(spatial=SpatialCoverage(
            territories=[t.reference() for t in territories],
            granularity=SPATIAL_GRANULARITIES.keys()[1]
        ))
        form = FakeForm(None, fake)
        self.assertEqual(form.spatial.territories._value(), ','.join([str(t.id) for t in territories]))

    def test_with_valid_territory_id(self):
        Fake, FakeForm = self.factory()
        territory = TerritoryFactory()

        fake = Fake()
        form = FakeForm(MultiDict({
            'spatial-territories': str(territory.id),
            'spatial-granularity': VALID_GRANULARITY
        }))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.territories), 1)
        self.assertEqual(fake.spatial.territories[0], territory.reference())
        self.assertTrue(shape(fake.spatial.geom).equals(shape(territory.geom)))

    def test_with_valid_territory_ids(self):
        Fake, FakeForm = self.factory()
        territories = [TerritoryFactory() for _ in range(3)]

        fake = Fake()
        form = FakeForm(MultiDict({
            'spatial-territories': ','.join([str(t.id) for t in territories]),
            'spatial-granularity': VALID_GRANULARITY
        }))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.territories), len(territories))
        expected_references = dict((str(t.id), t.reference()) for t in territories)
        for territory in fake.spatial.territories:
            self.assertIn(str(territory.id), expected_references)
            self.assertEqual(territory, expected_references[str(territory.id)])

        expected_geom = cascaded_union([shape(t.geom) for t in territories])
        self.assertTrue(shape(fake.spatial.geom).equals(expected_geom))

    def test_with_invalid_data(self):
        Fake, FakeForm = self.factory()

        form = FakeForm(MultiDict({'spatial-territories': 'wrong-data', 'spatial-granularity': 'wrong'}))

        form.validate()
        self.assertIn('spatial', form.errors)
        self.assertEqual(len(form.errors['spatial']), 2)

        self.assertIn('granularity', form.errors['spatial'])
        self.assertEqual(len(form.errors['spatial']['granularity']), 1)
        self.assertIn('territories', form.errors['spatial'])
        self.assertEqual(len(form.errors['spatial']['territories']), 1)

    def test_with_initial(self):
        Fake, FakeForm = self.factory()
        territories = [TerritoryFactory() for _ in range(3)]

        fake = Fake(spatial=SpatialCoverage(
            territories=[t.reference() for t in territories],
            granularity=SPATIAL_GRANULARITIES.keys()[1]
        ))

        territory = TerritoryFactory()
        data = MultiDict({
            'spatial-territories': str(territory.id),
            'spatial-granularity': VALID_GRANULARITY
        })

        form = FakeForm(data, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.territories), 1)
        self.assertEqual(fake.spatial.territories[0], territory.reference())
        self.assertTrue(shape(fake.spatial.geom).equals(shape(territory.geom)))

    def test_with_initial_none(self):
        Fake, FakeForm = self.factory()
        territory = TerritoryFactory()

        fake = Fake(spatial=None)
        form = FakeForm(MultiDict({
            'spatial-territories': str(territory.id),
            'spatial-granularity': VALID_GRANULARITY
        }), fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.territories), 1)
        self.assertEqual(fake.spatial.territories[0], territory.reference())
        self.assertTrue(shape(fake.spatial.geom).equals(shape(territory.geom)))
