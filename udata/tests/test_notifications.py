from datetime import datetime

import pytz
from flask import url_for

from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.organization.notifications import MembershipRequestNotification
from udata.core.user.factories import UserFactory
from udata.features.notifications import actions

from .api import APITestCase, DBTestCase


class NotificationsAPITest(APITestCase):
    def test_no_notifications(self):
        self.login()
        response = self.get(url_for("api.notifications"))
        self.assert200(response)

        self.assertEqual(response.json["total"], 0)

    def test_has_notifications(self):
        admin = self.login()
        self.login()
        organization = OrganizationFactory(members=[Member(user=admin, role="admin")])
        data = {"comment": "a comment"}

        response = self.post(url_for("api.request_membership", org=organization), data)
        self.assert201(response)

        self.login(admin)
        response = self.get(url_for("api.notifications"))
        self.assert200(response)

        self.assertEqual(response.json["total"], 1)
