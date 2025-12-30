from udata.core.organization.constants import CERTIFIED
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.notifications import (
    membership_request_notifications,
)
from udata.core.organization.tasks import notify_badge_certified
from udata.core.user.factories import UserFactory
from udata.features.notifications.models import Notification
from udata.models import Member, MembershipRequest
from udata.tests.api import APITestCase, DBTestCase, PytestOnlyDBTestCase
from udata.tests.helpers import assert_equal_dates


class OrganizationNotificationsTest(PytestOnlyDBTestCase):
    def test_pending_membership_requests(self):
        admin = UserFactory()
        editor = UserFactory()
        applicant = UserFactory()
        request = MembershipRequest(user=applicant, comment="test")
        members = [Member(user=editor, role="editor"), Member(user=admin, role="admin")]
        org = OrganizationFactory(members=members, requests=[request])

        assert len(membership_request_notifications(applicant)) == 0
        assert len(membership_request_notifications(editor)) == 0

        notifications = membership_request_notifications(admin)
        assert len(notifications) == 1
        dt, details = notifications[0]
        assert_equal_dates(dt, request.created)
        assert details["id"] == request.id
        assert details["organization"] == org.id
        assert details["user"]["id"] == applicant.id
        assert details["user"]["fullname"] == applicant.fullname
        assert details["user"]["avatar"] == str(applicant.avatar)


class MembershipRequestNotificationTest(DBTestCase):
    def test_notification_created_for_admins_only(self):
        """Notifications are created for all admin users, not editors"""
        admin1 = UserFactory()
        admin2 = UserFactory()
        editor = UserFactory()
        applicant = UserFactory()
        members = [
            Member(user=editor, role="editor"),
            Member(user=admin1, role="admin"),
            Member(user=admin2, role="admin"),
        ]
        org = OrganizationFactory(members=members)

        request = MembershipRequest(user=applicant, comment="test")
        org.add_membership_request(request)

        notifications = Notification.objects.all()
        assert len(notifications) == 2

        admin_users = [notif.user for notif in notifications]
        self.assertIn(admin1, admin_users)
        self.assertIn(admin2, admin_users)

        for notification in notifications:
            assert notification.details.request_organization == org
            assert notification.details.request_user == applicant
            assert_equal_dates(notification.created_at, request.created)

    def test_no_duplicate_notifications(self):
        """Duplicate notifications are not created on subsequent saves"""
        admin = UserFactory()
        applicant = UserFactory()
        org = OrganizationFactory(members=[Member(user=admin, role="admin")])

        request = MembershipRequest(user=applicant, comment="test")
        org.add_membership_request(request)
        org.add_membership_request(request)

        assert Notification.objects.count() == 1

    def test_multiple_requests_create_separate_notifications(self):
        """Multiple requests from different users create separate notifications"""
        admin = UserFactory()
        applicant1 = UserFactory()
        applicant2 = UserFactory()
        org = OrganizationFactory(members=[Member(user=admin, role="admin")])

        request1 = MembershipRequest(user=applicant1, comment="test 1")
        org.add_membership_request(request1)

        request2 = MembershipRequest(user=applicant2, comment="test 2")
        org.add_membership_request(request2)

        notifications = Notification.objects.all()
        assert len(notifications) == 2

        request_users = [notif.details.request_user for notif in notifications]
        self.assertIn(applicant1, request_users)
        self.assertIn(applicant2, request_users)


class CertifiedBadgeNotificationTest(APITestCase):
    def test_notification_created_for_all_members(self):
        """Notifications are created for all organization members when CERTIFIED badge is added"""
        member1 = UserFactory()
        member2 = UserFactory()
        member3 = UserFactory()
        members = [
            Member(user=member1, role="admin"),
            Member(user=member2, role="editor"),
            Member(user=member3, role="editor"),
        ]
        org = OrganizationFactory(members=members)

        # Add CERTIFIED badge (this calls notify_badge_certified task)
        notify_badge_certified(str(org.id))

        notifications = Notification.objects.all()
        assert len(notifications) == 3

        notified_users = [notif.user for notif in notifications]
        self.assertIn(member1, notified_users)
        self.assertIn(member2, notified_users)
        self.assertIn(member3, notified_users)

        for notification in notifications:
            assert notification.details.organization == org

    def test_notification_details_contain_organization_reference(self):
        """Notification details contain correct organization reference"""
        member = UserFactory()
        org = OrganizationFactory(members=[Member(user=member, role="admin")])

        notify_badge_certified(str(org.id))

        notification = Notification.objects.first()
        assert notification is not None
        assert notification.user == member
        assert notification.details.organization == org

    def test_notifications_filtered_by_organization(self):
        """Notifications can be filtered by organization"""
        member = UserFactory()
        org1 = OrganizationFactory(members=[Member(user=member, role="admin")])
        org2 = OrganizationFactory(members=[Member(user=member, role="editor")])

        notify_badge_certified(str(org1.id))
        notify_badge_certified(str(org2.id))

        # Verify filtering works correctly for each organization
        org1_notifications = Notification.objects.with_organization_in_details(org1)
        assert org1_notifications.count() == 1
        assert org1_notifications.first().details.organization == org1

        org2_notifications = Notification.objects.with_organization_in_details(org2)
        assert org2_notifications.count() == 1
        assert org2_notifications.first().details.organization == org2

    def test_notifications_cleaned_on_organization_purge(self):
        """Notifications are deleted when organization is purged"""
        from udata.core.organization.tasks import purge_organizations

        member = UserFactory()
        org1 = OrganizationFactory(members=[Member(user=member, role="admin")])
        org2 = OrganizationFactory(members=[Member(user=member, role="editor")])

        notify_badge_certified(str(org1.id))
        notify_badge_certified(str(org2.id))

        # Verify notifications exist for both organizations
        assert Notification.objects.count() == 2
        assert Notification.objects.with_organization_in_details(org1).count() == 1
        assert Notification.objects.with_organization_in_details(org2).count() == 1

        # Mark org1 as deleted and purge it
        from datetime import datetime
        org1.deleted = datetime.utcnow()
        org1.save()
        purge_organizations()

        # Verify org1 notifications are deleted but org2 notifications remain
        assert Notification.objects.count() == 1
        assert Notification.objects.with_organization_in_details(org1).count() == 0
        assert Notification.objects.with_organization_in_details(org2).count() == 1
        assert Notification.objects.first().details.organization == org2
