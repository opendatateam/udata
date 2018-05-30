# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from datetime import date, datetime

from werkzeug.datastructures import MultiDict

from udata.forms import fields, ModelForm
from udata.models import db

pytestmark = [
    pytest.mark.usefixtures('app')
]


class ExtrasFieldTest:

    def factory(self):
        class Fake(db.Document):
            extras = db.ExtrasField()

        class FakeForm(ModelForm):
            model_class = Fake
            extras = fields.ExtrasField()

        return Fake, FakeForm

    def test_empty_data(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        form = FakeForm()
        form.populate_obj(fake)

        assert fake.extras == {}

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
        assert form.errors == {}

        form.populate_obj(fake)

        assert fake.extras == {
            'integer': 42,
            'float': 42.0,
            'string': 'value',
            'datetime': now,
            'date': today,
            'bool': True
        }

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
        assert 'extras' in form.errors
        assert len(form.errors['extras']) == 1

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
        assert form.errors == {}

        form.populate_obj(fake)
        assert fake.extras == {
            'dict': {
                'integer': 42,
                'float': 42.0,
                'string': 'value',
            }
        }

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
        assert 'extras' in form.errors
        assert len(form.errors['extras']) == 1
