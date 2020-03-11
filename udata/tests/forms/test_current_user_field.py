from bson import ObjectId

from werkzeug.datastructures import MultiDict

from udata.auth import login_user
from udata.core.user.factories import UserFactory, AdminFactory
from udata.forms import ModelForm, fields
from udata.models import db, User
from udata.tests import TestCase


class CurrentUserFieldTest(TestCase):
    def factory(self, *args, **kwargs):
        class Ownable(db.Document):
            owner = db.ReferenceField(User)

        class OwnableForm(ModelForm):
            model_class = Ownable
            owner = fields.CurrentUserField(*args, **kwargs)

        return Ownable, OwnableForm

    def test_empty_values(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()

        login_user(user)

        form = OwnableForm()
        self.assertEqual(form.owner.data, user)

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertEqual(ownable.owner, user)

    def test_initial_value(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()

        login_user(user)
        ownable = Ownable(owner=user)

        form = OwnableForm(None, obj=ownable)
        self.assertEqual(form.owner.data, user)

    def test_with_valid_user_self(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()

        login_user(user)

        form = OwnableForm(MultiDict({
            'owner': str(user.id)
        }))

        self.assertEqual(form.owner.data, user)

        form.validate()
        self.assertEqual(form.errors, {})

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertEqual(ownable.owner, user)

    def test_with_other_user(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        other = UserFactory()

        login_user(user)

        form = OwnableForm(MultiDict({
            'owner': str(other.id)
        }))

        self.assertEqual(form.owner.data, other)

        form.validate()
        self.assertIn('owner', form.errors)
        self.assertEqual(len(form.errors['owner']), 1)

    def test_with_other_user_admin(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        admin = AdminFactory()

        login_user(admin)

        form = OwnableForm(MultiDict({
            'owner': str(user.id)
        }))

        self.assertEqual(form.owner.data, user)

        form.validate()
        self.assertEqual(form.errors, {})

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertEqual(ownable.owner, user)

    def test_with_valid_user_self_json(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        login_user(user)

        form = OwnableForm.from_json({
            'owner': str(user.id)
        })

        self.assertEqual(form.owner.data, user)

        form.validate()
        self.assertEqual(form.errors, {})

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertEqual(ownable.owner, user)

    def test_with_user_null_json(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        login_user(user)

        form = OwnableForm.from_json({
            'owner': None
        })

        self.assertEqual(form.owner.data, user)

        form.validate()
        self.assertEqual(form.errors, {})

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertEqual(ownable.owner, user)

    def test_with_user_object_self_from_json(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        login_user(user)

        form = OwnableForm.from_json({
            'owner': {'id': str(user.id)}
        })

        self.assertEqual(form.owner.data, user)

        form.validate()
        self.assertEqual(form.errors, {})

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertEqual(ownable.owner, user)

    def test_with_invalid_data(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()

        login_user(user)

        form = OwnableForm(MultiDict({
            'owner': str('wrongwith12c')
        }))

        form.validate()
        self.assertIn('owner', form.errors)
        self.assertEqual(len(form.errors['owner']), 1)

    def test_with_user_not_found(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()

        login_user(user)

        form = OwnableForm(MultiDict({
            'owner': str(ObjectId())
        }))

        form.validate()
        self.assertIn('owner', form.errors)
        self.assertEqual(len(form.errors['owner']), 1)

    def test_with_user_not_logged_found(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()

        form = OwnableForm(MultiDict({
            'owner': str(user.id)
        }))

        form.validate()
        self.assertIn('owner', form.errors)
        self.assertEqual(len(form.errors['owner']), 1)
