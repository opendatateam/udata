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


class FakeEmbedded(db.EmbeddedDocument):
    name = db.StringField()


class FakeAuditableSubject(Auditable, db.Document):
    name = field(db.StringField())
    tags = field(db.TagListField())
    some_date = field(db.DateField())
    daterange_embedded = field(db.EmbeddedDocumentField(db.DateRange))
    embedded_list = field(db.ListField(db.EmbeddedDocumentField("FakeEmbedded")))
    ref_list = field(db.ListField(db.ReferenceField("FakeSubject")))
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
                tags=["some", "tags"],
                some_date=date(2020, 1, 1),
                daterange_embedded={"start": date(2020, 1, 1), "end": date(2020, 12, 31)},
                embedded_list=[FakeEmbedded(name=f"fake_embedded_{i}") for i in range(3)],
                ref_list=[FakeSubject.objects.create(name=f"fake_ref_{i}") for i in range(3)],
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

        fake.daterange_embedded.start = date(2017, 7, 7)
        with assert_emit(post_save, FakeAuditableSubject.on_update):
            fake.save()

        fake.embedded_list[1].name = "other"
        with assert_emit(post_save, FakeAuditableSubject.on_update):
            fake.save()

        # Reference document field that should NOT trigger an update signal
        # on the current document
        fake.ref_list[1].name = "other"
        with assert_not_emit(FakeAuditableSubject.on_update):
            fake.ref_list[1].save()

        # Not auditable field that should NOT trigger an update signal
        fake.not_auditable = "changed"
        with assert_not_emit(FakeAuditableSubject.on_update):
            fake.save()

        # Field modifications that should NOT trigger an update signal
        # since they are actually cleaned and stored similarly to the current value
        # 1. Same as current ones but in capital case, that will be slugified
        fake.tags = ["OTHER", "TAGS"]
        with assert_not_emit(FakeAuditableSubject.on_update):
            fake.save()
            fake.reload()
            self.assertEqual(fake.tags, ["other", "tags"])

        # 2. Using a datetime, that will be stored as date in mongo, exactly like the current value
        fake.some_date = datetime(2027, 7, 7, 0, 0, 0)
        with assert_not_emit(FakeAuditableSubject.on_update):
            fake.save()
            fake.reload()
            self.assertEqual(fake.some_date, date(2027, 7, 7))

        # The deletion should trigger a delete signal
        with assert_not_emit(FakeAuditableSubject.on_update):
            fake.delete()

    def test_changed_fields(self):
        """It should emit an update signals on subject fields creation, update and deletion"""
        fake = FakeAuditableSubject.objects.create(
            name="fake",
            tags=["some", "tags"],
            some_date=date(2020, 1, 1),
            daterange_embedded={"start": date(2020, 1, 1), "end": date(2020, 12, 31)},
            embedded_list=[FakeEmbedded(name=f"fake_embedded_{i}") for i in range(3)],
            ref_list=[FakeSubject.objects.create(name=f"fake_ref_{i}") for i in range(3)],
            not_auditable="original",
        )

        def check_signal_update(args):
            self.assertEqual(
                args[1]["changed_fields"],
                [
                    "name",
                    "tags",
                    "some_date",
                    "daterange_embedded.start",
                    "daterange_embedded.end",
                    "embedded_list.1.name",
                ],
            )
            self.assertEqual(args[1]["previous"]["name"], "fake")
            self.assertEqual(args[1]["previous"]["tags"], ["some", "tags"])
            self.assertEqual(args[1]["previous"]["some_date"], date(2020, 1, 1))
            self.assertEqual(args[1]["previous"]["daterange_embedded.start"], date(2020, 1, 1))
            self.assertEqual(args[1]["previous"]["daterange_embedded.end"], date(2020, 12, 31))
            self.assertEqual(args[1]["previous"]["embedded_list.1.name"], "fake_embedded_1")

        with assert_emit(FakeAuditableSubject.on_update, assertions_callback=check_signal_update):
            fake.name = "different"
            fake.tags = ["other", "tags"]
            fake.some_date = date(2027, 7, 7)
            fake.daterange_embedded.start = date(2017, 7, 7)
            fake.daterange_embedded.end = date(2027, 7, 7)
            fake.embedded_list[1].name = "other"
            # Modification of a reference document should not be taken into account in changed_fields
            fake.ref_list[1].name = "other"
            fake.ref_list[1].save()
            fake.not_auditable = "changed"
            fake.save()
