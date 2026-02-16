from datetime import date, datetime
from uuid import UUID

import pytest
from mongoengine.fields import (
    BooleanField,
    DateTimeField,
    DictField,
    FloatField,
    IntField,
    StringField,
    UUIDField,
)
from werkzeug.datastructures import MultiDict

from udata.forms import ModelForm, fields
from udata.mongo import db
from udata.mongo.datetime_fields import DateField
from udata.mongo.extras_fields import ExtrasField
from udata.mongo.url_field import URLField
from udata.tests import PytestOnlyTestCase


class ExtrasFieldTest(PytestOnlyTestCase):
    def factory(self):
        class Fake(db.Document):
            extras = ExtrasField()

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

        now = datetime.utcnow()
        today = date.today()

        fake = Fake()
        form = FakeForm(
            MultiDict(
                {
                    "extras": {
                        "integer": 42,
                        "float": 42.0,
                        "string": "value",
                        "datetime": now,
                        "date": today,
                        "bool": True,
                        "dict": {
                            "integer": 42,
                            "float": 42.0,
                            "string": "value",
                        },
                    }
                }
            )
        )

        form.validate()
        assert form.errors == {}

        form.populate_obj(fake)

        assert fake.extras == {
            "integer": 42,
            "float": 42.0,
            "string": "value",
            "datetime": now,
            "date": today,
            "bool": True,
            "dict": {
                "integer": 42,
                "float": 42.0,
                "string": "value",
            },
        }

    def test_with_null_data(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        form = FakeForm(MultiDict({"extras": None}))

        form.validate()
        assert form.errors == {}

        form.populate_obj(fake)
        assert fake.extras == {}

    def test_with_valid_registered_data(self):
        Fake, FakeForm = self.factory()

        @Fake.extras("dict")
        class Custom(DictField):
            pass

        fake = Fake()
        form = FakeForm(
            MultiDict(
                {
                    "extras": {
                        "dict": {
                            "integer": 42,
                            "float": 42.0,
                            "string": "value",
                        }
                    }
                }
            )
        )

        form.validate()
        assert form.errors == {}

        form.populate_obj(fake)
        assert fake.extras == {
            "dict": {
                "integer": 42,
                "float": 42.0,
                "string": "value",
            }
        }

    @pytest.mark.parametrize(
        "dbfield,value,type,expected",
        [
            pytest.param(*p, id=p[0].__name__)
            for p in [
                (
                    DateTimeField,
                    "2018-05-29T13:15:04.397603",
                    datetime,
                    datetime(2018, 5, 29, 13, 15, 4, 397603),
                ),
                (DateField, "2018-05-29", date, date(2018, 5, 29)),
                (BooleanField, "true", bool, True),
                (IntField, 42, int, 42),
                (StringField, "42", str, "42"),
                (FloatField, "42.0", float, 42.0),
                (URLField, "http://test.com", str, "http://test.com"),
                (
                    UUIDField,
                    "e3b06d6d-90c0-4407-adc0-de81d327f181",
                    UUID,
                    UUID("e3b06d6d-90c0-4407-adc0-de81d327f181"),
                ),
            ]
        ],
    )
    def test_can_parse_registered_data(self, dbfield, value, type, expected):
        Fake, FakeForm = self.factory()

        Fake.extras.register("my:extra", dbfield)

        fake = Fake()
        form = FakeForm(MultiDict({"extras": {"my:extra": value}}))

        form.validate()
        assert form.errors == {}

        form.populate_obj(fake)

        assert isinstance(fake.extras["my:extra"], type)
        assert fake.extras["my:extra"] == expected

    @pytest.mark.parametrize(
        "dbfield,value",
        [
            pytest.param(*p, id=p[0].__name__)
            for p in [
                (DateTimeField, "xxxx"),
                (DateField, "xxxx"),
                (IntField, "xxxx"),
                (StringField, 42),
                (FloatField, "xxxx"),
                (URLField, "not-an-url"),
                (UUIDField, "not-a-uuid"),
            ]
        ],
    )
    def test_fail_bad_registered_data(self, dbfield, value):
        Fake, FakeForm = self.factory()

        Fake.extras.register("my:extra", dbfield)

        form = FakeForm(MultiDict({"extras": {"my:extra": value}}))

        form.validate()
        assert "extras" in form.errors
        assert "my:extra" in form.errors["extras"]
