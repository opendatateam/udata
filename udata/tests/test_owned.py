from mongoengine import post_save

import udata.core.owned as owned
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Organization
from udata.core.user.factories import AdminFactory, UserFactory
from udata.core.user.models import User
from udata.models import Member
from udata.mongo import db
from udata.tests import DBTestMixin, TestCase


class CustomQuerySet(owned.OwnedQuerySet):
    def visible(self):
        return self(private__ne=True)


class Owned(owned.Owned, db.Document):
    name = db.StringField()
    private = db.BooleanField()

    meta = {
        "queryset_class": CustomQuerySet,
    }


class OwnedPostSave(owned.Owned, db.Document):
    @classmethod
    def post_save(cls, sender, document, **kwargs):
        if "post_save" in kwargs.get("ignores", []):
            return
        if kwargs.get("created"):
            pass
        else:
            # on update
            compute_some_metrics(document, **kwargs)


def compute_some_metrics(document, **kwargs):
    document.metric = 0
    document.save(signal_kwargs={"ignores": ["post_save"]})


class TestOwnedMixin(DBTestMixin, TestCase):
    def test_fields(self):
        self.assertIsInstance(Owned.owner, db.ReferenceField)
        self.assertEqual(Owned.owner.document_type_obj, User)

        self.assertIsInstance(Owned.organization, db.ReferenceField)
        self.assertEqual(Owned.organization.document_type_obj, Organization)

    def test_owner_changed_from_user_to_user(self):
        first_owner = UserFactory()
        second_owner = UserFactory()
        owned = Owned.objects.create(owner=first_owner)

        def handler(document, previous):
            self.assertEqual(document, owned)
            self.assertEqual(document.owner, second_owner)
            self.assertIsNone(document.organization)
            self.assertEqual(previous, first_owner)
            handler.called = True

        with Owned.on_owner_change.connected_to(handler):
            owned.owner = second_owner
            owned.save()

        self.assertTrue(getattr(handler, "called", False))

    def test_owner_changed_from_user_to_org(self):
        owner = UserFactory()
        org = OrganizationFactory()
        owned = Owned.objects.create(owner=owner)

        def handler(document, previous):
            self.assertEqual(document, owned)
            self.assertIsNone(document.owner)
            self.assertEqual(document.organization, org)
            self.assertEqual(previous, owner)
            handler.called = True

        with Owned.on_owner_change.connected_to(handler):
            owned.organization = org
            owned.save()

        self.assertTrue(getattr(handler, "called", False))

    def test_owner_changed_from_org_to_org(self):
        first_org = OrganizationFactory()
        second_org = OrganizationFactory()
        owned = Owned.objects.create(organization=first_org)

        def handler(document, previous):
            self.assertEqual(document, owned)
            self.assertIsNone(document.owner)
            self.assertEqual(document.organization, second_org)
            self.assertEqual(previous, first_org)
            handler.called = True

        with Owned.on_owner_change.connected_to(handler):
            owned.organization = second_org
            owned.save()

        self.assertTrue(getattr(handler, "called", False))

    def test_owner_changed_from_org_to_user(self):
        user = UserFactory()
        org = OrganizationFactory()
        owned = Owned.objects.create(organization=org)

        def handler(document, previous):
            self.assertEqual(document, owned)
            self.assertEqual(document.owner, user)
            self.assertIsNone(document.organization)
            self.assertEqual(previous, org)
            handler.called = True

        with Owned.on_owner_change.connected_to(handler):
            owned.owner = user
            owned.save()

        self.assertTrue(getattr(handler, "called", False))

    def test_owner_changed_from_org_to_user_with_owned_postsave_signal(self):
        # Test with an additionnal post save signal that will retriger save signals
        user = UserFactory()
        org = OrganizationFactory()

        owned = OwnedPostSave.objects.create(organization=org)

        with post_save.connected_to(OwnedPostSave.post_save, sender=OwnedPostSave):
            owned.owner = user
            owned.save()

        assert owned.owner == user
        assert owned.organization is None


class OwnedQuerysetTest(DBTestMixin, TestCase):
    def test_queryset_type(self):
        self.assertIsInstance(Owned.objects, owned.OwnedQuerySet)

    def test_owned_by_user(self):
        user = UserFactory()
        owned = Owned.objects.create(owner=user)
        Owned.objects.create(owner=UserFactory())

        result = Owned.objects.owned_by(user)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], owned)

    def test_owned_by_org(self):
        org = OrganizationFactory()
        owned = Owned.objects.create(organization=org)
        Owned.objects.create(organization=OrganizationFactory())

        result = Owned.objects.owned_by(org)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], owned)

    def test_owned_by_org_or_user(self):
        user = UserFactory()
        org = OrganizationFactory()
        owneds = [Owned.objects.create(owner=user), Owned.objects.create(organization=org)]
        excluded = [
            Owned.objects.create(owner=UserFactory()),
            Owned.objects.create(organization=OrganizationFactory()),
        ]

        result = Owned.objects.owned_by(org, user)

        self.assertEqual(len(result), 2)
        for owned_ in result:
            self.assertIn(owned_, owneds)

        for owned_ in excluded:
            self.assertNotIn(owned_, result)

    def test_visible_by_user(self) -> None:
        admin: User = AdminFactory()
        user: User = UserFactory()
        member = Member(user=user, role="editor")
        other_user: User = UserFactory()
        org: Organization = OrganizationFactory(members=[member])
        other_org: Organization = OrganizationFactory()
        owned_by_user: Owned = Owned.objects.create(owner=user, name="owned_by_user")
        owned_by_org: Owned = Owned.objects.create(organization=org, name="owned_by_org")
        owned_by_other_user: Owned = Owned.objects.create(
            owner=other_user, name="owned_by_other_user"
        )
        owned_by_other_org: Owned = Owned.objects.create(
            organization=other_org, name="owned_by_other_org"
        )
        private_owned_by_user: Owned = Owned.objects.create(
            owner=user, private=True, name="private_owned_by_user"
        )
        private_owned_by_org: Owned = Owned.objects.create(
            organization=org, private=True, name="private_owned_by_org"
        )
        private_owned_by_other_user: Owned = Owned.objects.create(
            owner=other_user, private=True, name="private_owned_by_other_user"
        )
        private_owned_by_other_org: Owned = Owned.objects.create(
            organization=other_org, private=True, name="private_owned_by_other_org"
        )

        visible_by_user: list[Owned] = [
            owned_by_user,
            owned_by_org,
            owned_by_other_user,
            owned_by_other_org,
            private_owned_by_user,
            private_owned_by_org,
        ]
        visible_by_other_user: list[Owned] = [
            private_owned_by_other_user,
            private_owned_by_other_org,
        ]

        # Admin can view everything.
        result: owned.OwnedQuerySet = Owned.objects.visible_by_user(
            admin, Owned.objects.visible()._query_obj
        )
        # 4 public + 1 private owned by user + 1 private owned by the user's org.
        self.assertEqual(len(result), 8)
        for owned_ in visible_by_user + visible_by_other_user:
            self.assertIn(owned_, result)

        result = Owned.objects.visible_by_user(user, Owned.objects.visible()._query_obj)
        # 4 public + 1 private owned by user + 1 private owned by the user's org.
        self.assertEqual(len(result), 6)
        for owned_ in visible_by_user:
            self.assertIn(owned_, result)

        # `.visible_by_user` does not reset other queries.
        result = Owned.objects(name="owned_by_user").visible_by_user(
            user, Owned.objects.visible()._query_obj
        )
        self.assertEqual(len(result), 1)
        self.assertIn(owned_by_user, result)
        result = Owned.objects.visible_by_user(user, Owned.objects.visible()._query_obj).filter(
            name="owned_by_user"
        )
        self.assertEqual(len(result), 1)
        self.assertIn(owned_by_user, result)

        result = Owned.objects(name="private_owned_by_user").visible_by_user(
            user, Owned.objects.visible()._query_obj
        )
        self.assertEqual(len(result), 1)
        self.assertIn(private_owned_by_user, result)
        result = Owned.objects.visible_by_user(user, Owned.objects.visible()._query_obj).filter(
            name="private_owned_by_user"
        )
        self.assertEqual(len(result), 1)
        self.assertIn(private_owned_by_user, result)

        result = Owned.objects(name="private_owned_by_other_user").visible_by_user(
            user, Owned.objects.visible()._query_obj
        )
        self.assertEqual(len(result), 0)
        result = Owned.objects.visible_by_user(user, Owned.objects.visible()._query_obj).filter(
            name="private_owned_by_other_user"
        )
        self.assertEqual(len(result), 0)
