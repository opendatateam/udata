from udata.auth import login_user
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.models import Activity, db
from udata.tests import DBTestMixin, TestCase, WebTestMixin


class FakeSubject(db.Document):
    name = db.StringField()


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
