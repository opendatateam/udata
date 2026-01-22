from flask import url_for

from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member

from . import PytestOnlyAPITestCase


class NotificationsAPITest(PytestOnlyAPITestCase):
    def test_no_notifications(self):
        # Test that a user has no notifications
        self.login()
        response = self.get(url_for("api.notifications"))
        self.assert200(response)
        assert response.json["total"] == 0

    def test_has_notifications(self):
        # Test that a user has notifications
        admin = self.login()
        self.login()
        organization = OrganizationFactory(members=[Member(user=admin, role="admin")])
        data = {"comment": "a comment"}

        response = self.post(url_for("api.request_membership", org=organization), data)
        self.assert201(response)

        self.login(admin)
        response = self.get(url_for("api.notifications"))
        self.assert200(response)
        assert response.json["total"] == 1
        assert response.json["data"][0]["details"]["request_organization"]["id"] == str(organization.id)

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
        assert response.json["total"] == 1
        notification_id = response.json["data"][0]["id"]

        # Now mark the notification as read
        response = self.post(url_for("api.read_notifications", notification=notification_id))
        self.assert200(response)

        # Verify the notification is marked as handled
        assert response.json["handled_at"] is not None

        # Verify that the notification no longer appears in the list of pending notifications
        response = self.get(url_for("api.notifications", handled=False))
        self.assert200(response)
        assert response.json["total"] == 0

    def test_read_notification_permission(self):
        """Test that only the user of a notification can mark it as read"""
        # Create a certified organization which should create a notification
        admin = self.login()
        organization = OrganizationFactory(members=[Member(user=admin, role="admin")])

        # Add CERTIFIED badge to organization to trigger notification
        organization.add_badge("certified")
        organization.save()

        # Get the notification first
        response = self.get(url_for("api.notifications"))
        self.assert200(response)
        assert response.json["total"] == 1
        notification_id = response.json["data"][0]["id"]

        # Login as a different user who doesn't own the notification
        self.login()
        # Try to mark the notification as read - should fail
        response = self.post(url_for("api.read_notifications", notification=notification_id))
        self.assert403(response)