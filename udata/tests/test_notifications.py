# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from datetime import datetime

from udata.features.notifications.actions import (
    register_provider, list_providers, notifier, get_notifications
)

from . import TestCase, DBTestMixin
from .factories import UserFactory


class NotificationsTest(TestCase, DBTestMixin):
    def test_registered_provider_is_listed(self):
        def fake_provider(user):
            pass

        register_provider('fake', fake_provider)

        self.assertIn('fake', list_providers())

    def test_registered_provider_with_decorator_is_listed(self):
        @notifier('fake')
        def fake_provider(user):
            pass

        self.assertIn('fake', list_providers())

    def test_registered_provider_provide_values(self):
        dt = datetime.now()

        def fake_provider(user):
            return [(dt, {'some': 'value'})]

        register_provider('fake', fake_provider)

        user = UserFactory()
        notifs = get_notifications(user)

        self.assertEqual(notifs, [{
            'type': 'fake',
            'created_on': dt,
            'details': {
                'some': 'value'
            }
        }])

