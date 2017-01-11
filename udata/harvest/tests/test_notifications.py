# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.tests import TestCase, DBTestMixin
from udata.core.user.factories import UserFactory, AdminFactory

from .factories import HarvestSourceFactory

from udata.tests.test_notifications import NotificationsMixin

from udata.harvest.notifications import validate_harvester_notifications


class HarvestNotificationsTest(NotificationsMixin, DBTestMixin, TestCase):
    def test_pending_harvester_validations(self):
        source = HarvestSourceFactory()
        admin = AdminFactory()
        user = UserFactory()

        self.assertEqual(len(validate_harvester_notifications(user)), 0)

        notifications = validate_harvester_notifications(admin)

        self.assertEqual(len(notifications), 1)
        dt, details = notifications[0]
        self.assertEqualDates(dt, source.created_at)
        self.assertEqual(details['id'], source.id)
        self.assertEqual(details['name'], source.name)
