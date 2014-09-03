# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.datastructures import MultiDict

from udata.forms import Form, fields
from udata.models import db, SpatialCoverage
from udata.tests import TestCase
from udata.tests.factories import TerritoryFactory, faker


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
        self.assertEqual(form.spatial._value(), '')
        self.assertIsNone(form.spatial.data)

        fake = Fake()
        form.populate_obj(fake)
        self.assertIsNone(fake.spatial)

    def test_initial_value_with_territories(self):
        Fake, FakeForm = self.factory()
        territories = [TerritoryFactory() for _ in range(3)]

        fake = Fake(spatial=SpatialCoverage(territories=[t.reference() for t in territories]))
        form = FakeForm(None, fake)
        self.assertEqual(form.spatial._value(), ','.join([str(t.id) for t in territories]))

    def test_with_valid_territory_id(self):
        Fake, FakeForm = self.factory()
        territory = TerritoryFactory()

        fake = Fake()
        form = FakeForm(MultiDict({'spatial': str(territory.id)}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.spatial.territories), 1)
        self.assertEqual(fake.spatial.territories[0], territory.reference())

    def test_with_invalid_data(self):
        Fake, FakeForm = self.factory()

        form = FakeForm(MultiDict({'spatial': 'wrong-data'}))

        form.validate()
        self.assertIn('spatial', form.errors)
        self.assertEqual(len(form.errors['spatial']), 1)
