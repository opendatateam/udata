# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.datastructures import MultiDict

from udata.forms import ModelForm, fields
from udata.models import db
from udata.tests import TestCase
from udata.utils import faker


class Nested(db.Document):
    name = db.StringField()


class Fake(db.Document):
    name = db.StringField()
    nested = db.ListField(db.ReferenceField(Nested))


class NestedListField(fields.ModelList, fields.Field):
    model = Nested


class FakeForm(ModelForm):
    model_class = Fake
    name = fields.StringField()
    nested = NestedListField()


class ModelListFieldTest(TestCase):
    def test_empty_data(self):
        fake = Fake()
        form = FakeForm()
        form.populate_obj(fake)

        self.assertEqual(fake.nested, [])

    def test_with_one_valid_data(self):
        nested = Nested.objects.create(name=faker.name())
        fake = Fake()
        form = FakeForm(MultiDict({'nested': str(nested.id)}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 1)
        self.assertIsInstance(fake.nested[0], Nested)
        self.assertEqual(fake.nested[0], nested)

    def test_with_multiple_valid_data(self):
        nesteds = [Nested.objects.create(name=faker.name()) for _ in range(3)]
        ids = [str(n.id) for n in nesteds]
        fake = Fake()
        form = FakeForm(MultiDict({'nested': ','.join(ids)}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), len(nesteds))
        self.assertIsInstance(fake.nested[0], Nested)
        self.assertEqual(fake.nested, nesteds)

    def test_with_one_valid_json_id(self):
        nested = Nested.objects.create(name=faker.name())
        fake = Fake()
        form = FakeForm.from_json({'nested': [str(nested.id)]})

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 1)
        self.assertIsInstance(fake.nested[0], Nested)
        self.assertEqual(fake.nested[0], nested)

    def test_with_one_valid_json_object(self):
        nested = Nested.objects.create(name=faker.name())
        fake = Fake()
        form = FakeForm.from_json({'nested': [{'id': str(nested.id)}]})

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 1)
        self.assertIsInstance(fake.nested[0], Nested)
        self.assertEqual(fake.nested[0], nested)

    def test_with_multiple_valid_json_id(self):
        nested = [Nested.objects.create(name=faker.name()) for _ in range(3)]
        ids = [str(n.id) for n in nested]
        fake = Fake()
        form = FakeForm.from_json({'nested': ids})

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), len(nested))
        self.assertIsInstance(fake.nested[0], Nested)
        self.assertEqual(fake.nested, nested)

    def test_with_multiple_valid_json_object(self):
        nested = [Nested.objects.create(name=faker.name()) for _ in range(3)]
        ids = [{'id': str(n.id)} for n in nested]
        fake = Fake()
        form = FakeForm.from_json({'nested': ids})

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), len(nested))
        self.assertIsInstance(fake.nested[0], Nested)
        self.assertEqual(fake.nested, nested)
