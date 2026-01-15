from flask import url_for

from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member

from .api import APITestCase


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
        self.assertEqual(
            response.json["data"][0]["details"]["request_organization"]["id"], str(organization.id)
        )

    def test_read_notification(self):
        """Test marking a notification as read"""
        # Create a certified organization which should create a notification
        admin = self.login()
        organization = OrganizationFactory(members=[Member(user=admin, role="admin")])
        
        # Add CERTIFIED badge to organization to trigger notification
        organization.add_badge("certified")
        organization.save()

        # Get the notification first
        response = self.get(url_for("api.notifications"))
        self.assert200(response)
        self.assertEqual(response.json["total"], 1)
        notification_id = response.json["data"][0]["id"]

        # Now mark the notification as read
        response = self.post(url_for("api.read_notifications", notification=notification_id))
        self.assert200(response)

        # Verify the notification is marked as handled
        self.assertIsNotNone(response.json["handled_at"])
        
        # Verify that the notification no longer appears in the list of pending notifications
        response = self.get(url_for("api.notifications", handled=False))
        self.assert200(response)
        self.assertEqual(response.json["total"], 0)
