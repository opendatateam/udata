from bson import ObjectId

from werkzeug.datastructures import MultiDict

from udata.auth import login_user
from udata.core.user.factories import UserFactory, AdminFactory
from udata.core.organization.factories import OrganizationFactory
from udata.forms import ModelForm, fields
from udata.models import db, User, Organization, Member
from udata.tests import TestCase


class PublishFieldTest(TestCase):
    def factory(self, *args, **kwargs):
        class Ownable(db.Document):
            owner = db.ReferenceField(User)
            organization = db.ReferenceField(Organization)

        class OwnableForm(ModelForm):
            model_class = Ownable

            owner = fields.CurrentUserField()
            organization = fields.PublishAsField(*args, **kwargs)

        return Ownable, OwnableForm

    def test_empty_values_not_logged(self):
        Ownable, OwnableForm = self.factory()

        form = OwnableForm()

        self.assertIsNone(form.owner.data)
        self.assertIsNone(form.organization.data)

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertIsNone(ownable.owner)
        self.assertIsNone(ownable.organization)

    def test_empty_values_logged(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()

        login_user(user)

        form = OwnableForm()

        self.assertEqual(form.owner.data, user)
        self.assertIsNone(form.organization.data)

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertEqual(ownable.owner, user)
        self.assertIsNone(ownable.organization)

    def test_with_initial_owner(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        ownable = Ownable(owner=user)

        form = OwnableForm(None, obj=ownable)
        self.assertEqual(form.owner.data, user)
        self.assertIsNone(form.organization.data)

    def test_with_initial_organization(self):
        Ownable, OwnableForm = self.factory()
        org = OrganizationFactory()
        ownable = Ownable(organization=org)

        form = OwnableForm(None, obj=ownable)
        self.assertIsNone(form.owner.data)
        self.assertEqual(form.organization.data, org)

    def test_with_initial_organization_and_user_logged(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        org = OrganizationFactory()
        ownable = Ownable(organization=org)

        login_user(user)

        form = OwnableForm(None, obj=ownable)
        self.assertIsNone(form.owner.data)
        self.assertEqual(form.organization.data, org)

    def test_with_valid_organization(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])

        login_user(user)

        form = OwnableForm(MultiDict({
            'organization': str(org.id)
        }))

        self.assertEqual(form.owner.data, user)
        self.assertEqual(form.organization.data, org)

        form.validate()
        self.assertEqual(form.errors, {})

        self.assertIsNone(form.owner.data)
        self.assertEqual(form.organization.data, org)

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertIsNone(ownable.owner)
        self.assertEqual(ownable.organization, org)

    def test_organization_over_owner(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])

        login_user(user)

        form = OwnableForm(MultiDict({
            'owner': str(user.id),
            'organization': str(org.id)
        }))

        self.assertEqual(form.owner.data, user)
        self.assertEqual(form.organization.data, org)

        form.validate()
        self.assertEqual(form.errors, {})

        self.assertIsNone(form.owner.data)
        self.assertEqual(form.organization.data, org)

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertIsNone(ownable.owner)
        self.assertEqual(ownable.organization, org)

    def test_with_valid_organization_from_json(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])

        login_user(user)

        form = OwnableForm.from_json({
            'organization': str(org.id)
        })

        self.assertEqual(form.owner.data, user)
        self.assertEqual(form.organization.data, org)

        form.validate()
        self.assertEqual(form.errors, {})

        self.assertIsNone(form.owner.data)
        self.assertEqual(form.organization.data, org)

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertIsNone(ownable.owner)
        self.assertEqual(ownable.organization, org)

    def test_with_organization_object_from_json(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])

        login_user(user)

        form = OwnableForm.from_json({
            'organization': {'id': str(org.id)}
        })

        self.assertEqual(form.organization.data, org)

        form.validate()
        self.assertEqual(form.errors, {})

        ownable = Ownable()
        form.populate_obj(ownable)
        self.assertIsNone(ownable.owner)
        self.assertEqual(ownable.organization, org)

    def test_with_invalid_data(self):
        Ownable, OwnableForm = self.factory()

        form = OwnableForm(MultiDict({
            'organization': str('wrongwith12c')
        }))

        form.validate()
        self.assertIn('organization', form.errors)
        self.assertEqual(len(form.errors['organization']), 1)

    def test_with_organization_not_found(self):
        Ownable, OwnableForm = self.factory()

        form = OwnableForm(MultiDict({
            'organization': str(ObjectId())
        }))

        form.validate()
        self.assertIn('organization', form.errors)
        self.assertEqual(len(form.errors['organization']), 1)

    def test_with_initial_and_both_member(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        org = OrganizationFactory(members=[Member(user=user, role='editor')])
        neworg = OrganizationFactory(
            members=[Member(user=user, role='editor')])
        ownable = Ownable(organization=org)

        form = OwnableForm(MultiDict({
            'organization': str(neworg.id)
        }), obj=ownable)

        self.assertEqual(form.organization.data, neworg)

        login_user(user)
        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(ownable)
        self.assertIsNone(ownable.owner)
        self.assertEqual(ownable.organization, neworg)

    def test_with_initial_and_not_member(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        org = OrganizationFactory(members=[Member(user=user, role='editor')])
        neworg = OrganizationFactory()
        ownable = Ownable(organization=org)

        form = OwnableForm(MultiDict({
            'organization': str(neworg.id)
        }), obj=ownable)

        self.assertEqual(form.organization.data, neworg)

        login_user(user)
        form.validate()
        self.assertIn('organization', form.errors)
        self.assertEqual(len(form.errors['organization']), 1)

    def test_not_member(self):
        Ownable, OwnableForm = self.factory()
        member = Member(user=UserFactory(), role='editor')
        org = OrganizationFactory(members=[member])

        login_user(UserFactory())

        form = OwnableForm(MultiDict({
            'organization': str(org.id)
        }))

        self.assertEqual(form.organization.data, org)

        self.assertFalse(form.validate())
        self.assertIn('organization', form.errors)
        self.assertEqual(len(form.errors['organization']), 1)

    def test_no_user_logged_in_permission(self):
        Ownable, OwnableForm = self.factory()
        member = Member(user=UserFactory(), role='editor')
        org = OrganizationFactory(members=[member])

        form = OwnableForm(MultiDict({
            'organization': str(org.id)
        }))

        self.assertEqual(form.organization.data, org)

        self.assertFalse(form.validate())
        self.assertIn('organization', form.errors)
        self.assertEqual(len(form.errors['organization']), 1)

    def test_set_organization_if_permissions(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        member = Member(user=user, role='editor')
        org = OrganizationFactory(members=[member])
        ownable = Ownable(owner=user)

        login_user(user)

        form = OwnableForm(MultiDict({
            'organization': str(org.id)
        }), obj=ownable)

        self.assertTrue(form.validate())
        self.assertEqual(form.errors, {})

        form.populate_obj(ownable)
        self.assertIsNone(ownable.owner)
        self.assertEqual(ownable.organization, org)

    def test_admin_can_set_owner(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        org = OrganizationFactory()
        ownable = Ownable(organization=org)

        login_user(AdminFactory())

        form = OwnableForm(MultiDict({
            'owner': str(user.id)
        }), obj=ownable)

        self.assertEqual(form.owner.data, user)
        self.assertEqual(form.organization.data, org)

        self.assertTrue(form.validate())
        self.assertEqual(form.errors, {})

        self.assertEqual(form.owner.data, user)
        self.assertIsNone(form.organization.data)

        form.populate_obj(ownable)
        self.assertEqual(ownable.owner, user)
        self.assertIsNone(ownable.organization)

    def test_admin_can_set_organization(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        org = OrganizationFactory()
        ownable = Ownable(owner=user)

        login_user(AdminFactory())

        form = OwnableForm(MultiDict({
            'organization': str(org.id)
        }), obj=ownable)

        self.assertEqual(form.owner.data, user)
        self.assertEqual(form.organization.data, org)

        self.assertTrue(form.validate())
        self.assertEqual(form.errors, {})

        self.assertIsNone(form.owner.data)
        self.assertEqual(form.organization.data, org)

        form.populate_obj(ownable)
        self.assertIsNone(ownable.owner)
        self.assertEqual(ownable.organization, org)

    def test_with_initial_org_and_no_data_provided(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        org = OrganizationFactory(members=[Member(user=user, role='editor')])
        ownable = Ownable(organization=org)

        form = OwnableForm(MultiDict({}), obj=ownable)

        self.assertEqual(form.organization.data, org)

        login_user(user)
        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(ownable)
        self.assertIsNone(ownable.owner)
        self.assertEqual(ownable.organization, org)

    def test_with_initial_owner_and_no_data_provided(self):
        Ownable, OwnableForm = self.factory()
        user = UserFactory()
        ownable = Ownable(owner=user)

        form = OwnableForm(MultiDict({}), obj=ownable)

        self.assertEqual(form.owner.data, user)

        login_user(user)
        form.validate()
        self.assertEqual(form.errors, {})

        form.populate_obj(ownable)
        self.assertEqual(ownable.owner, user)
        self.assertIsNone(ownable.organization)
