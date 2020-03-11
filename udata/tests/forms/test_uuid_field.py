import uuid

from werkzeug.datastructures import MultiDict

from udata.forms import Form, fields
from udata.models import db
from udata.tests import TestCase


class UUIDFieldTest(TestCase):
    def factory(self):
        class Fake(db.Document):
            id = db.AutoUUIDField()

        class FakeForm(Form):
            id = fields.UUIDField()

        return Fake, FakeForm

    def test_empty_data(self):
        Fake, FakeForm = self.factory()

        form = FakeForm()
        self.assertEqual(form.id.data, None)

        fake = Fake()
        form.populate_obj(fake)
        self.assertIsNone(fake.id)

    def test_initial_values(self):
        Fake, FakeForm = self.factory()

        fake = Fake(id=uuid.uuid4())
        form = FakeForm(None, obj=fake)
        self.assertEqual(form.id.data, fake.id)

    def test_with_valid_uuid_string(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        id = uuid.uuid4()
        form = FakeForm(MultiDict({
            'id': str(id)
        }))

        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.id, id)

    def test_with_valid_uuid_string_from_json(self):
        Fake, FakeForm = self.factory()

        fake = Fake()
        id = uuid.uuid4()
        form = FakeForm(MultiDict({
            'id': str(id)
        }))

        form = FakeForm.from_json({'id': str(id)})
        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(fake)

        self.assertEqual(fake.id, id)

    def test_with_invalid_uuid_string(self):
        Fake, FakeForm = self.factory()

        form = FakeForm(MultiDict({'id': 'not-an-uuid'}))

        form.validate()
        self.assertIn('id', form.errors)
        self.assertEqual(len(form.errors['id']), 1)
