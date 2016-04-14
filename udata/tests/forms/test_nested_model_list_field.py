# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from werkzeug.datastructures import MultiDict

from udata.forms import ModelForm, fields
from udata.models import db
from udata.tests import TestCase
from udata.utils import faker


class SubNested(db.EmbeddedDocument):
    name = db.StringField(required=True)


class Nested(db.EmbeddedDocument):
    id = db.AutoUUIDField()
    name = db.StringField()
    sub = db.EmbeddedDocumentField(SubNested)
    raw = db.DictField()


class Fake(db.Document):
    name = db.StringField()
    nested = db.ListField(db.EmbeddedDocumentField(Nested))


class SubNestedForm(ModelForm):
    model_class = SubNested
    name = fields.StringField(validators=[fields.validators.required()])


class NestedForm(ModelForm):
    model_class = Nested
    name = fields.StringField(validators=[fields.validators.required()])


class NestedFormWithId(NestedForm):
    id = fields.UUIDField()


class NestedFormWithSub(NestedFormWithId):
    sub = fields.FormField(SubNestedForm)


class NestedModelListFieldTest(TestCase):
    def factory(self, data=None, instance=None, id=True, sub=False, **kwargs):
        if sub:
            nested_form = NestedFormWithSub
        elif id:
            nested_form = NestedFormWithId
        else:
            nested_form = NestedForm

        class FakeForm(ModelForm):
            model_class = Fake
            name = fields.StringField()
            nested = fields.NestedModelList(nested_form, **kwargs)

        if isinstance(data, MultiDict):
            return FakeForm(data, obj=instance, instance=instance)
        else:
            return FakeForm.from_json(data, obj=instance, instance=instance)

    def test_empty_data(self):
        fake = Fake()
        form = self.factory()
        form.populate_obj(fake)

        self.assertEqual(fake.nested, [])

    def test_with_one_valid_data(self):
        fake = Fake()
        form = self.factory(MultiDict({'nested-0-name': 'John Doe'}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 1)
        self.assertIsInstance(fake.nested[0], Nested)
        self.assertEqual(fake.nested[0].name, 'John Doe')

    def test_with_one_valid_json(self):
        fake = Fake()
        form = self.factory({'nested': [{'name': 'John Doe'}]})

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 1)
        self.assertIsInstance(fake.nested[0], Nested)
        self.assertEqual(fake.nested[0].name, 'John Doe')

    def test_with_multiple_valid_data(self):
        fake = Fake()
        form = self.factory(MultiDict([
            ('nested-0-name', faker.name()),
            ('nested-1-name', faker.name()),
            ('nested-2-name', faker.name()),
        ]))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 3)
        for nested in fake.nested:
            self.assertIsInstance(nested, Nested)

    def test_with_multiple_valid_json(self):
        fake = Fake()
        form = self.factory({'nested': [
            {'name': faker.name()},
            {'name': faker.name()},
            {'name': faker.name()},
        ]})

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 3)
        for nested in fake.nested:
            self.assertIsInstance(nested, Nested)

    def test_with_initial_elements(self):
        fake = Fake.objects.create(nested=[
            Nested(name=faker.name()),
            Nested(name=faker.name()),
        ])
        order = [n.id for n in fake.nested]
        form = self.factory({'nested': [
            {'id': str(fake.nested[0].id)},
            {'id': str(fake.nested[1].id)},
            {'name': faker.name()},
        ]}, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 3)
        for idx, id in enumerate(order):
            self.assertEqual(fake.nested[idx].id, id)
        self.assertIsNotNone(fake.nested[2].id)

    def test_with_nested_initial_elements(self):
        fake = Fake.objects.create(nested=[
            Nested(name=faker.name(), sub=SubNested(name=faker.word())),
            Nested(name=faker.name(), sub=SubNested(name=faker.word())),
        ])
        order = [n.id for n in fake.nested]
        data = [
            {'id': str(fake.nested[0].id)},
            {'id': str(fake.nested[1].id)},
            {'name': faker.name(), 'sub': {'name': faker.name()}},
        ]
        form = self.factory({'nested': data}, fake, sub=True)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 3)
        for idx, id in enumerate(order):
            nested = fake.nested[idx]
            self.assertEqual(nested.id, id)
            self.assertIsNotNone(nested.sub)
            self.assertIsNotNone(nested.sub.name)
        self.assertIsNotNone(fake.nested[2].id)
        self.assertEqual(fake.nested[2].sub.name, data[2]['sub']['name'])

    def test_with_initial_elements_as_ids(self):
        fake = Fake.objects.create(nested=[
            Nested(name=faker.name()),
            Nested(name=faker.name()),
        ])
        order = [n.id for n in fake.nested]
        form = self.factory({'nested': [
            str(fake.nested[0].id),
            str(fake.nested[1].id),
            {'name': faker.name()},
        ]}, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 3)
        for idx, id in enumerate(order):
            self.assertEqual(fake.nested[idx].id, id)
        self.assertIsNotNone(fake.nested[2].id)

    def test_with_non_submitted_initial_elements(self):
        fake = Fake.objects.create(nested=[
            Nested(name=faker.name()),
            Nested(name=faker.name()),
        ])
        initial = [(n.id, n.name) for n in fake.nested]
        form = self.factory({'name': faker.word()}, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), len(initial))
        for idx, (id, name) in enumerate(initial):
            nested = fake.nested[idx]
            self.assertEqual(nested.id, id)
            self.assertEqual(nested.name, name)

    def test_update_initial_elements(self):
        fake = Fake.objects.create(nested=[
            Nested(name=faker.name()),
            Nested(name=faker.name()),
        ])
        initial = [n.id for n in fake.nested]
        form = self.factory({'nested': [
            {'id': str(fake.nested[0].id), 'name': faker.name()},
            {'id': str(fake.nested[1].id), 'name': faker.name()},
            {'name': faker.name()},
        ]}, fake)
        names = [n['name'] for n in form.data['nested']]

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), 3)
        for idx, id in enumerate(initial):
            nested = fake.nested[idx]
            self.assertEqual(nested.id, id)
            self.assertEqual(nested.name, names[idx])
        self.assertIsNotNone(fake.nested[2].id)

    def test_non_submitted_subnested(self):
        form = self.factory({'nested': [
            {'name': faker.name()},
            {'name': faker.name(), 'sub': {'name': faker.name()}},
        ]}, sub=True)

        form.validate()
        self.assertEqual(form.errors, {})

        fake = form.save()

        self.assertEqual(len(fake.nested), 2)
        self.assertIsNone(fake.nested[0].sub)
        self.assertIsNotNone(fake.nested[1].sub)

    def test_reorder_initial_elements(self):
        fake = Fake.objects.create(nested=[
            Nested(name=faker.name()),
            Nested(name=faker.name()),
            Nested(name=faker.name()),
            Nested(name=faker.name()),
        ])
        initial = [(n.id, n.name) for n in fake.nested]
        new_order = [1, 2, 3, 0]
        form = self.factory({'nested': [
            {'id': str(fake.nested[i].id)} for i in new_order
        ]}, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), len(initial))
        for nested, old_idx in zip(fake.nested, new_order):
            id, name = initial[old_idx]
            self.assertEqual(nested.id, id)
            self.assertEqual(nested.name, name)

    def test_reorder_initial_elements_with_raw(self):
        fake = Fake.objects.create(nested=[
            Nested(name=faker.name(), raw={'test': 0}),
            Nested(name=faker.name(), raw={'test': 1}),
            Nested(name=faker.name(), raw={'test': 2}),
            Nested(name=faker.name(), raw={'test': 3}),
        ])
        initial = [(n.id, n.name) for n in fake.nested]

        new_order = [1, 2, 3, 0]
        form = self.factory({'nested': [
            {'id': str(fake.nested[i].id)} for i in new_order
        ]}, fake)

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(len(fake.nested), len(initial))
        for nested, old_idx in zip(fake.nested, new_order):
            id, name = initial[old_idx]
            self.assertEqual(nested.id, id)
            self.assertEqual(nested.name, name)
            self.assertEqual(nested.raw['test'], old_idx)
