from datetime import date, datetime

import pytest
from werkzeug.datastructures import MultiDict

from udata.forms import ModelForm, fields
from udata.mongo import db

pytestmark = [pytest.mark.usefixtures("app")]


class DictFieldTest:
    def factory(self):
        class Fake(db.Document):
            raw = db.DictField()

        class FakeForm(ModelForm):
            model_class = Fake
            raw = fields.DictField()

        return Fake, FakeForm

    def test_empty_data(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        form = FakeForm()
        form.populate_obj(fake)

        assert fake.raw == {}

    def test_with_valid_data(self):
        Fake, FakeForm = self.factory()

        now = datetime.utcnow()
        today = date.today()

        fake = Fake()
        form = FakeForm(
            MultiDict(
                {
                    "raw": {
                        "integer": 42,
                        "float": 42.0,
                        "string": "value",
                        "datetime": now,
                        "date": today,
                        "bool": True,
                        "dict": {"key": "value"},
                    }
                }
            )
        )

        form.validate()
        assert form.errors == {}

        form.populate_obj(fake)

        assert fake.raw == {
            "integer": 42,
            "float": 42.0,
            "string": "value",
            "datetime": now,
            "date": today,
            "bool": True,
            "dict": {"key": "value"},
        }

    def test_with_invalid_data(self):
        Fake, FakeForm = self.factory()

        form = FakeForm(MultiDict({"raw": 42}))

        form.validate()
        assert "raw" in form.errors
        assert len(form.errors["raw"]) == 1
