from datetime import date, timedelta

from werkzeug.datastructures import MultiDict

from udata.forms import Form, fields
from udata.mongo import db
from udata.tests import TestCase
from udata.utils import to_iso_date


class DateRangeFieldTest(TestCase):
    def factory(self):
        class Fake(db.Document):
            daterange = db.EmbeddedDocumentField(db.DateRange)

        class FakeForm(Form):
            daterange = fields.DateRangeField()

        return Fake, FakeForm

    def test_empty_data(self):
        Fake, FakeForm = self.factory()

        form = FakeForm()
        self.assertEqual(form.daterange._value(), "")
        self.assertEqual(form.daterange.data, None)

        fake = Fake()
        form.populate_obj(fake)
        self.assertIsNone(fake.daterange)

    def test_initial_values(self):
        Fake, FakeForm = self.factory()
        dr = db.DateRange(start=date.today() - timedelta(days=1), end=date.today())

        fake = Fake(daterange=dr)
        form = FakeForm(None, obj=fake)
        expected = " - ".join([to_iso_date(dr.start), to_iso_date(dr.end)])
        self.assertEqual(form.daterange._value(), expected)

    def test_with_valid_dates(self):
        Fake, FakeForm = self.factory()
        start = date.today() - timedelta(days=1)
        end = date.today()
        expected = " - ".join([to_iso_date(start), to_iso_date(end)])

        fake = Fake()
        form = FakeForm(MultiDict({"daterange": expected}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.daterange, db.DateRange(start=start, end=end))

    def test_with_valid_dates_from_json(self):
        Fake, FakeForm = self.factory()
        start = date.today() - timedelta(days=1)
        end = date.today()

        fake = Fake()
        form = FakeForm.from_json(
            {
                "daterange": {
                    "start": to_iso_date(start),
                    "end": to_iso_date(end),
                }
            }
        )

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.daterange, db.DateRange(start=start, end=end))

    def test_with_invalid_dates(self):
        Fake, FakeForm = self.factory()

        form = FakeForm(MultiDict({"daterange": "XXX - ZZZ"}))

        form.validate()
        self.assertIn("daterange", form.errors)
        self.assertEqual(len(form.errors["daterange"]), 1)

    def test_with_invalid_format(self):
        Fake, FakeForm = self.factory()
        start = date.today() - timedelta(days=1)
        end = date.today()
        wrong = " xx ".join([to_iso_date(start), to_iso_date(end)])

        form = FakeForm(MultiDict({"daterange": wrong}))

        form.validate()
        self.assertIn("daterange", form.errors)
        self.assertEqual(len(form.errors["daterange"]), 1)

    def test_with_invalid_dates_from_json(self):
        Fake, FakeForm = self.factory()

        form = FakeForm.from_json({"daterange": {"start": "XXX", "end": "ZZZ"}})

        form.validate()
        self.assertIn("daterange", form.errors)
        self.assertEqual(len(form.errors["daterange"]), 1)

    def test_with_invalid_json_format(self):
        Fake, FakeForm = self.factory()
        start = date.today() - timedelta(days=1)
        end = date.today()

        form = FakeForm.from_json(
            {
                "daterange": {
                    "a": to_iso_date(start),
                    "b": to_iso_date(end),
                }
            }
        )

        form.validate()
        self.assertIn("daterange", form.errors)
        self.assertEqual(len(form.errors["daterange"]), 1)
