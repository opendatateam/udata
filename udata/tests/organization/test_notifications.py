from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.notifications import (
    membership_request_notifications,
)
from udata.core.user.factories import UserFactory
from udata.features.notifications.models import Notification
from udata.models import Member, MembershipRequest
from udata.tests.api import DBTestCase, PytestOnlyDBTestCase
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
