from werkzeug.datastructures import MultiDict

from udata.forms import Form, fields
from udata.mongo import db
from udata.tests import TestCase
from udata.utils import faker


class UrlFieldTest(TestCase):
    def factory(self):
        class Fake(db.Document):
            url = db.URLField()

        class FakeForm(Form):
            url = fields.URLField()

        return Fake, FakeForm

    def test_empty_data(self):
        Fake, FakeForm = self.factory()

        form = FakeForm()
        self.assertEqual(form.url.data, None)

        fake = Fake()
        form.populate_obj(fake)
        self.assertIsNone(fake.url)

    def test_initial_values(self):
        Fake, FakeForm = self.factory()

        fake = Fake(url=faker.url())
        form = FakeForm(None, obj=fake)
        self.assertEqual(form.url.data, fake.url)

    def test_with_valid_url(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        url = faker.url()
        form = FakeForm(MultiDict({"url": url}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.url, url)

    def test_with_valid_url_is_stripped(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        url = faker.url()
        form = FakeForm(MultiDict({"url": url + "   "}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.url, url)

    def test_with_invalid_url(self):
        Fake, FakeForm = self.factory()

        form = FakeForm(MultiDict({"url": "this-is-not-an-url"}))

        form.validate()
        self.assertIn("url", form.errors)
        self.assertEqual(len(form.errors["url"]), 1)

    def test_with_unicode_url(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        url = "https://www.somewhère.com/with/accënts/"
        form = FakeForm(MultiDict({"url": url}))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.url, url)
