# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, datetime

from werkzeug.datastructures import MultiDict

from udata.forms import Form, fields
from udata.models import db
from udata.tests import TestCase


class ExtrasFieldTest(TestCase):

    def factory(self):
        class Fake(db.Document):
            extras = db.ExtrasField()

        class FakeForm(Form):
            extras = fields.ExtrasField(extras=Fake.extras)

        return Fake, FakeForm

    def test_empty_data(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        form = FakeForm()
        form.populate_obj(fake)

        self.assertEqual(fake.extras, {})

    def test_with_valid_data(self):
        Fake, FakeForm = self.factory()

        now = datetime.now()
        today = date.today()

        fake = Fake()
        form = FakeForm(MultiDict({'extras': {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
            'datetime': now,
            'date': today,
            'bool': True,
        }}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.extras, {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
            'datetime': now,
            'date': today,
            'bool': True
        })

    def test_with_invalid_data(self):
        Fake, FakeForm = self.factory()

        form = FakeForm(MultiDict({'extras': {
            'dict': {
                'integer': 42,
                'float': 42.0,
                'string': 'value',
            }
        }}))

        form.validate()
        self.assertIn('extras', form.errors)
        self.assertEqual(len(form.errors['extras']), 1)

    def test_with_valid_registered_data(self):
        Fake, FakeForm = self.factory()

        @Fake.extras('dict')
        class ExtraDict(db.Extra):
            def validate(self, value):
                if not isinstance(value, dict):
                    raise db.ValidationError('Should be a dict instance')

        fake = Fake()
        form = FakeForm(MultiDict({'extras': {
            'dict': {
                'integer': 42,
                'float': 42.0,
                'string': 'value',
            }
        }}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)
        self.assertEqual(fake.extras, {
            'dict': {
                'integer': 42,
                'float': 42.0,
                'string': 'value',
            }
        })

    def test_with_invalid_registered_data(self):
        Fake, FakeForm = self.factory()

        @Fake.extras('dict')
        class ExtraDict(db.Extra):
            def validate(self, value):
                if not isinstance(value, dict):
                    raise db.ValidationError('Should be a dict instance')

        form = FakeForm(MultiDict({'extras': {
            'dict': 42
        }}))

        form.validate()
        self.assertIn('extras', form.errors)
        self.assertEqual(len(form.errors['extras']), 1)
