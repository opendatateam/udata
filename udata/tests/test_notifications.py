from datetime import datetime

from flask import url_for

from udata.features.notifications import actions
from udata.core.user.factories import UserFactory

from . import TestCase, DBTestMixin
from .api import APITestCase


class NotificationsMixin(object):
    def setUp(self):
        actions._providers = {}


class NotificationsActionsTest(NotificationsMixin, TestCase, DBTestMixin):
    def test_registered_provider_is_listed(self):
        def fake_provider(user):
            return []

        actions.register_provider('fake', fake_provider)

        self.assertIn('fake', actions.list_providers())

    def test_registered_provider_with_decorator_is_listed(self):
        @actions.notifier('fake')
        def fake_provider(user):
            return []

        self.assertIn('fake', actions.list_providers())

    def test_registered_provider_provide_values(self):
        dt = datetime.now()

        def fake_provider(user):
            return [(dt, {'some': 'value'})]

        actions.register_provider('fake', fake_provider)

        user = UserFactory()
        notifs = actions.get_notifications(user)

        self.assertEqual(len(notifs), 1)
        self.assertEqual(notifs[0]['type'], 'fake')
        self.assertEqual(notifs[0]['details'], {'some': 'value'})
        self.assertEqualDates(notifs[0]['created_on'], dt)


class NotificationsAPITest(NotificationsMixin, APITestCase):
    def test_no_notifications(self):
        self.login()
        response = self.get(url_for('api.notifications'))
        self.assert200(response)

        self.assertEqual(len(response.json), 0)

    def test_has_notifications(self):
        self.login()
        dt = datetime.now()

        @actions.notifier('fake')
        def fake_notifier(user):
            return [(dt, {'some': 'value'}), (dt, {'another': 'value'})]

        response = self.get(url_for('api.notifications'))
        self.assert200(response)

        self.assertEqual(len(response.json), 2)

        for notification in response.json:
            self.assertEqual(notification['created_on'], dt.isoformat())
            self.assertEqual(notification['type'], 'fake')
        self.assertEqual(response.json[0]['details'], {'some': 'value'})
        self.assertEqual(response.json[1]['details'], {'another': 'value'})
