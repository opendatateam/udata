# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from udata.models import db, Activity
from udata.tests import TestCase, DBTestMixin, WebTestMixin

from udata.tests.factories import OrganizationFactory


class FakeModel(db.Document):
    name = db.StringField()


class FakeActivity(Activity):
    data = db.ReferenceField(FakeModel)


class ActivityTest(WebTestMixin, DBTestMixin, TestCase):
    def setUp(self):
        self.fake = FakeModel.objects.create(name='fake')
        self.login()

    def test_create_and_retrieve_for_user(self):
        FakeActivity.objects.create(actor=self.user)

        activities = Activity.objects(actor=self.user)

        self.assertEqual(len(activities), 1)
        self.assertIsInstance(activities[0], FakeActivity)

    def test_create_and_retrieve_for_org(self):
        org = OrganizationFactory()
        FakeActivity.objects.create(actor=self.user, as_organization=org)

        activities = Activity.objects(as_organization=org)

        self.assertEqual(len(activities), 1)
        self.assertIsInstance(activities[0], FakeActivity)

    def check_emitted(self, sender, activity):
        self.assertEqual(sender, FakeActivity)
        self.assertIsInstance(activity, FakeActivity)
        self.emitted = True

    def test_emit_signal(self):
        '''It should emit a signal on new activity'''
        self.emitted = False
        with FakeActivity.on_new.connected_to(self.check_emitted):
            FakeActivity.objects.create(actor=self.user)

        self.assertTrue(self.emitted)
