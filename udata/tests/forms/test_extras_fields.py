# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from datetime import date, datetime
from uuid import UUID

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

    def test_with_null_data(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        form = FakeForm(MultiDict({'extras': None}))

        form.validate()
        assert form.errors == {}

        form.populate_obj(fake)
        assert fake.extras == {}

    def test_with_valid_registered_data(self):
        Fake, FakeForm = self.factory()

        @Fake.extras('dict')
        class Custom(db.DictField):
            pass

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

    @pytest.mark.parametrize('dbfield,value,type,expected', [
        pytest.param(*p, id=p[0].__name__) for p in [
            (db.DateTimeField, '2018-05-29T13:15:04.397603', datetime,
                datetime(2018, 5, 29, 13, 15, 4, 397603)),
            (db.DateField, '2018-05-29', date, date(2018, 5, 29)),
            (db.BooleanField, 'true', bool, True),
            (db.IntField, 42, int, 42),
            (db.StringField, '42', basestring, '42'),
            (db.FloatField, '42.0', float, 42.0),
            (db.URLField, 'http://test.com', basestring, 'http://test.com'),
            (db.UUIDField, 'e3b06d6d-90c0-4407-adc0-de81d327f181', UUID,
                UUID('e3b06d6d-90c0-4407-adc0-de81d327f181')),
    ]])
    def test_can_parse_registered_data(self, dbfield, value, type, expected):
        Fake, FakeForm = self.factory()

        Fake.extras.register('my:extra', dbfield)

        fake = Fake()
        form = FakeForm(MultiDict({'extras': {'my:extra': value}}))

        form.validate()
        assert form.errors == {}

        form.populate_obj(fake)

        assert isinstance(fake.extras['my:extra'], type)
        assert fake.extras['my:extra'] == expected

    @pytest.mark.parametrize('dbfield,value', [
        pytest.param(*p, id=p[0].__name__) for p in [
            (db.DateTimeField, 'xxxx'),
            (db.DateField, 'xxxx'),
            (db.IntField, 'xxxx'),
            (db.StringField, 42),
            (db.FloatField, 'xxxx'),
            (db.URLField, 'not-an-url'),
            (db.UUIDField, 'not-a-uuid'),
    ]])
    def test_fail_bad_registered_data(self, dbfield, value):
        Fake, FakeForm = self.factory()

        Fake.extras.register('my:extra', dbfield)

        form = FakeForm(MultiDict({'extras': {'my:extra': value}}))

        form.validate()
        assert 'extras' in form.errors
        assert 'my:extra' in form.errors['extras']
