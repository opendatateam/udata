from udata.core.organization.constants import CERTIFIED, PUBLIC_SERVICE
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.user.factories import UserFactory
from udata.features.notifications.models import Notification
from udata.tests.api import APITestCase
from udata.tests.helpers import capture_mails


class NotifyBadgeCertifiedTest(APITestCase):
    def test_notify_badge_certified_creates_notifications(self):
        """
        Test that notify_badge_certified creates in-app notifications for organization members
        """
        # Create users and organization
        user1 = UserFactory()
        user2 = UserFactory()

        # Create organization with members
        organization = OrganizationFactory(
            members=[Member(user=user1, role="admin"), Member(user=user2, role="editor")]
        )
        org_mails = [user1.email, user2.email]

        with capture_mails() as mails:
            # Add CERTIFIED badge to organization
            organization.add_badge(CERTIFIED)
            self.assertEqual(len(mails), 2)
            self.assertIn(mails[0].recipients[0], org_mails)
            self.assertIn(mails[1].recipients[0], org_mails)

        # Verify that notifications were created for each member
        notifications = Notification.objects(user__in=[user1, user2])
        assert len(notifications) == 2

        # Verify that notifications are for the correct organization
        for notification in notifications:
            assert notification.details.organization.id == organization.id
            assert notification.details.organization.name == organization.name

    def test_notify_badge_certified_notification_details(self):
        """
        Test that notifications have correct details for CERTIFIED badge
        """
        # Create users and organization
        user = UserFactory()
        organization = OrganizationFactory(members=[Member(user=user, role="admin")])

        with capture_mails():
            # Add PUBLIC_SERVICE badge to organization
            organization.add_badge(CERTIFIED)

        # Get the notification
        notification = Notification.objects.first()

        # Verify notification details
        assert notification is not None
        assert notification.details.organization.id == organization.id
        assert notification.details.organization.name == organization.name
        assert notification.user == user


class NotifyBadgePublicServiceTest(APITestCase):
    def test_notify_badge_public_service_creates_notifications(self):
        """
        Test that notify_badge_public_service creates in-app notifications for organization members
        """
        # Create users and organization
        user1 = UserFactory()
        user2 = UserFactory()

        # Create organization with members
        organization = OrganizationFactory(
            members=[Member(user=user1, role="admin"), Member(user=user2, role="editor")]
        )
        org_mails = [user1.email, user2.email]

        with capture_mails() as mails:
            # Add PUBLIC_SERVICE badge to organization
            organization.add_badge(PUBLIC_SERVICE)
            self.assertEqual(len(mails), 2)
            self.assertIn(mails[0].recipients[0], org_mails)
            self.assertIn(mails[1].recipients[0], org_mails)

        # Verify that notifications were created for each member
        notifications = Notification.objects(user__in=[user1, user2])
        assert len(notifications) == 2

        # Verify that notifications are for the correct organization
        for notification in notifications:
            assert notification.details.organization.id == organization.id
            assert notification.details.organization.name == organization.name

    def test_notify_badge_public_service_notification_details(self):
        """
        Test that notifications have correct details for PUBLIC_SERVICE badge
        """
        # Create users and organization
        user = UserFactory()
        organization = OrganizationFactory(members=[Member(user=user, role="admin")])

        with capture_mails():
            # Add PUBLIC_SERVICE badge to organization
            organization.add_badge(PUBLIC_SERVICE)

        # Get the notification
        notification = Notification.objects.first()

        # Verify notification details
        assert notification is not None
        assert notification.details.organization.id == organization.id
        assert notification.details.organization.name == organization.name
        assert notification.user == user
