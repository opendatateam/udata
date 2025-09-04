from datetime import date, datetime

from blinker import Signal
from mongoengine.signals import post_save

from udata.api_fields import field
from udata.auth import login_user
from udata.core.activity.models import Activity, Auditable
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.models import db
from udata.tests import DBTestMixin, TestCase, WebTestMixin
from udata.tests.helpers import assert_emit, assert_not_emit


class FakeSubject(db.Document):
    name = db.StringField()


class FakeAuditableSubject(Auditable, db.Document):
    name = field(db.StringField())
    tags = field(db.TagListField())
    some_date = field(db.DateField())
    not_auditable = field(db.StringField(), auditable=False)

    after_save = Signal()
    on_create = Signal()
    on_update = Signal()
    on_delete = Signal()


post_save.connect(FakeAuditableSubject.post_save, sender=FakeAuditableSubject)


class FakeActivity(Activity):
    key = "fake"
    related_to = db.ReferenceField(FakeSubject)


class ActivityTest(WebTestMixin, DBTestMixin, TestCase):
    def setUp(self):
        self.fake = FakeSubject.objects.create(name="fake")
        self.login()

    def test_create_and_retrieve_for_user(self):
        FakeActivity.objects.create(actor=self.user, related_to=self.fake)

        activities = Activity.objects(actor=self.user)

        self.assertEqual(len(activities), 1)
        self.assertIsInstance(activities[0], FakeActivity)

    def test_create_and_retrieve_with_extras(self):
        FakeActivity.objects.create(
            actor=self.user,
            related_to=self.fake,
            extras={"some_key": "some_value", "other_key": "other_value"},
        )

        activities = Activity.objects(actor=self.user)

        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0].extras["some_key"], "some_value")
        self.assertEqual(activities[0].extras["other_key"], "other_value")
        self.assertIsInstance(activities[0], FakeActivity)

    def test_create_and_retrieve_for_org(self):
        org = OrganizationFactory()
        FakeActivity.objects.create(actor=self.user, related_to=self.fake, organization=org)

        activities = Activity.objects(organization=org)

        self.assertEqual(len(activities), 1)
        self.assertIsInstance(activities[0], FakeActivity)

    def test_create_and_retrieve_for_related(self):
        org = OrganizationFactory()
        FakeActivity.objects.create(actor=self.user, related_to=self.fake, organization=org)
        FakeActivity.objects.create(actor=UserFactory(), related_to=self.fake)

        activities = Activity.objects(related_to=self.fake)

        self.assertEqual(len(activities), 2)
        for activity in activities:
            self.assertIsInstance(activity, FakeActivity)

    def check_emitted(self, sender, activity):
        self.assertEqual(sender, FakeActivity)
        self.assertIsInstance(activity, FakeActivity)
        self.emitted = True

    def test_emit_signal(self):
        """It should emit a signal on new activity"""
        self.emitted = False
        with FakeActivity.on_new.connected_to(self.check_emitted):
            FakeActivity.objects.create(actor=self.user, related_to=self.fake)

        self.assertTrue(self.emitted)

    def test_class_shortcut(self):
        """It should emit a signal on new activity"""
        self.emitted = False
        self.login()
        with self.app.app_context():
            login_user(self.user)
            with FakeActivity.on_new.connected_to(self.check_emitted):
                FakeActivity.emit(self.fake)

        self.assertTrue(self.emitted)

        self.assertEqual(Activity.objects(related_to=self.fake).count(), 1)
        self.assertEqual(Activity.objects(actor=self.user).count(), 1)


class AuditableTest(WebTestMixin, DBTestMixin, TestCase):
    def test_auditable_signals_emission(self):
        """It should emit appropriate signals on subject fields creation, update and deletion"""
        with assert_emit(post_save, FakeAuditableSubject.on_create):
            fake = FakeAuditableSubject.objects.create(
                name="fake",
                tags=["my", "tags"],
                some_date=date(2020, 1, 1),
                not_auditable="original",
            )

        # All these fields should trigger an update signal
        fake.name = "different"
        with assert_emit(post_save, FakeAuditableSubject.on_update):
            fake.save()

        fake.tags = ["other", "tags"]
        with assert_emit(post_save, FakeAuditableSubject.on_update):
            fake.save()

        fake.some_date = date(2027, 7, 7)
        with assert_emit(post_save, FakeAuditableSubject.on_update):
            fake.save()

        # Not auditable field that should NOT trigger an update signal
        fake.not_auditable = "changed"
        with assert_not_emit(FakeAuditableSubject.on_update):
            fake.save()

        # Field modifications that should NOT trigger an update signal
        # since they are actually cleaned and stored similarly to the current value
        # 1. Same as current ones but in capital case, that will be slugified
        fake.tags = ["OTHER", "TAGS"]
        with assert_not_emit(FakeAuditableSubject.on_update):  # FAIL at the moment
            fake.save()
            fake.reload()
            self.assertEqual(fake.tags, ["other", "tags"])

        # 2. Using a datetime, that will be stored as date in mongo, exactly like the current value
        fake.some_date = datetime(2027, 7, 7, 0, 0, 0)
        with assert_not_emit(FakeAuditableSubject.on_update):  # FAIL at the moment
            fake.save()
            fake.reload()
            self.assertEqual(fake.some_date, date(2027, 7, 7))

        # The deletion should trigger a delete signal
        with assert_not_emit(FakeAuditableSubject.on_update):
            fake.delete()

    def test_changed_fields(self):
        """It should emit an update signals on subject fields creation, update and deletion"""
        fake = FakeAuditableSubject.objects.create(
            name="fake", tags=["my", "tags"], some_date=date(2020, 1, 1), not_auditable="original"
        )

        def check_signal_update(args):
            self.assertEqual(args[1]["changed_fields"], ["name", "tags", "some_date"])
            self.assertEqual(args[1]["previous"]["name"], "fake")
            self.assertEqual(args[1]["previous"]["tags"], ["my", "tags"])
            self.assertEqual(args[1]["previous"]["some_date"], date(2020, 1, 1))

        with assert_emit(FakeAuditableSubject.on_update, assertions_callback=check_signal_update):
            fake.name = "different"
            fake.tags = ["other", "tags"]
            fake.some_date = date(2027, 7, 7)
            fake.not_auditable = "changed"
            fake.save()
