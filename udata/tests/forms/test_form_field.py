# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.datastructures import MultiDict

from udata.forms import ModelForm, fields
from udata.models import db
from udata.tests import TestCase
from udata.utils import faker


class Nested(db.EmbeddedDocument):
    id = db.AutoUUIDField()
    name = db.StringField(required=True)


class Fake(db.Document):
    name = db.StringField()
    nested = db.EmbeddedDocumentField(Nested)


class NestedForm(ModelForm):
    model_class = Nested
    name = fields.StringField(validators=[fields.validators.DataRequired()])


class NestedFormWithId(NestedForm):
    id = fields.UUIDField()


class FormFieldTest(TestCase):
    def factory(self, data=None, instance=None, id=True, **kwargs):
        if id:
            nested_form = NestedFormWithId
        else:
            nested_form = NestedForm

        class FakeForm(ModelForm):
            model_class = Fake
            name = fields.StringField()
            nested = fields.FormField(nested_form, **kwargs)

        if isinstance(data, MultiDict):
            return FakeForm(data, obj=instance, instance=instance)
        else:
            return FakeForm.from_json(data, obj=instance, instance=instance)

    def test_empty_data(self):
        fake = Fake()
        form = self.factory()
        form.populate_obj(fake)

        self.assertIsNone(fake.nested)

    def test_with_one_valid_data(self):
        fake = Fake()
        form = self.factory(MultiDict({'nested-name': 'John Doe'}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertIsInstance(fake.nested, Nested)
        self.assertEqual(fake.nested.name, 'John Doe')

    def test_with_one_valid_json(self):
        fake = Fake()
        form = self.factory({'nested': {'name': 'John Doe'}})

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertIsInstance(fake.nested, Nested)
        self.assertEqual(fake.nested.name, 'John Doe')

    def test_with_initial_elements(self):
        fake = Fake.objects.create(nested=Nested(name=faker.name()))
        new_name = faker.name()
        form = self.factory({'nested': {'name': new_name}}, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertIsNotNone(fake.nested.id)
        self.assertEqual(fake.nested.name, new_name)

    def test_with_non_submitted_initial_elements(self):
        fake = Fake.objects.create(nested=Nested(name=faker.name()))
        initial_id = fake.nested.id
        initial_name = fake.nested.name
        form = self.factory({'name': faker.word()}, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.nested.id, initial_id)
        self.assertEqual(fake.nested.name, initial_name)

    def test_update_initial_elements(self):
        fake = Fake.objects.create(nested=Nested(name=faker.name()))
        initial_id = fake.nested.id
        new_name = faker.name()
        form = self.factory({'nested': {'name': new_name}}, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.nested.id, initial_id)
        self.assertEqual(fake.nested.name, new_name)

    def test_create_with_non_submitted_elements(self):
        form = self.factory({'name': faker.word()})

        form.validate()
        self.assertEqual(form.errors, {})

        fake = form.save()

        self.assertIsNotNone(fake.name)
        self.assertIsNone(fake.nested)
