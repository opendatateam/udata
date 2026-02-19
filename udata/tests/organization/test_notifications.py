from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.notifications import (
    MembershipAcceptedNotificationDetails,
    MembershipRefusedNotificationDetails,
    membership_request_notifications,
)
from udata.core.organization.tasks import notify_membership_response
from udata.core.user.factories import UserFactory
from udata.features.notifications.models import Notification
from udata.models import Member, MembershipRequest
from udata.tests.api import DBTestCase, PytestOnlyAPITestCase, PytestOnlyDBTestCase
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


class MembershipResponseNotificationTest(PytestOnlyAPITestCase):
    def test_accept_membership_creates_notification(self):
        """Accepting a membership request creates a notification for the applicant"""

        applicant = UserFactory()
        admin = UserFactory()
        self.login(admin)
        membership_request = MembershipRequest(user=applicant, comment="test", status="pending")
        org = OrganizationFactory(
            members=[Member(user=admin, role="admin")], requests=[membership_request]
        )

        # Accept the membership request and notify
        membership_request.status = "accepted"
        org.save()
        notify_membership_response(org.id, str(membership_request.id))

        notifications = Notification.objects(user=applicant).all()
        assert len(notifications) == 1

        notification = notifications[0]
        assert notification.user == applicant
        assert notification.details.organization == org
        assert isinstance(notification.details, MembershipAcceptedNotificationDetails)

    def test_refuse_membership_creates_notification(self):
        """Refusing a membership request creates a notification for the applicant"""

        applicant = UserFactory()
        admin = UserFactory()
        self.login(admin)
        membership_request = MembershipRequest(user=applicant, comment="test", status="pending")
        org = OrganizationFactory(
            members=[Member(user=admin, role="admin")], requests=[membership_request]
        )

        # Refuse the membership request and notify
        membership_request.status = "refused"
        org.save()
        notify_membership_response(org.id, str(membership_request.id))

        notifications = Notification.objects(user=applicant).all()
        assert len(notifications) == 1

        notification = notifications[0]
        assert notification.user == applicant
        assert notification.details.organization == org
        assert isinstance(notification.details, MembershipRefusedNotificationDetails)

    def test_full_membership_request_cycle_with_refusal_then_approval(self):
        """Test full cycle: request -> refused -> new request -> approved"""
        from datetime import datetime

        applicant = UserFactory()
        admin = UserFactory()
        org = OrganizationFactory(members=[Member(user=admin, role="admin")])

        # Step 1: Applicant requests membership
        first_request = MembershipRequest(user=applicant, comment="I want to join")
        org.add_membership_request(first_request)

        org.reload()
        assert len(org.pending_requests) == 1

        admin_notifications = Notification.objects(user=admin).all()
        assert len(admin_notifications) == 1
        assert admin_notifications[0].details.request_user == applicant
        assert admin_notifications[0].details.request_organization == org
        assert admin_notifications[0].handled_at is None

        # Step 2: Admin refuses the request
        first_request = org.requests[0]
        first_request.status = "refused"
        first_request.handled_by = admin
        first_request.handled_on = datetime.utcnow()
        first_request.refusal_comment = "Not now"
        org.save()
        MembershipRequest.after_handle.send(first_request, org=org)
        notify_membership_response(org.id, str(first_request.id))

        org.reload()
        assert len(org.pending_requests) == 0
        assert len(org.refused_requests) == 1
        assert not org.is_member(applicant)

        admin_notifications = Notification.objects(user=admin).all()
        assert len(admin_notifications) == 1
        assert admin_notifications[0].handled_at is not None

        applicant_notifications = Notification.objects(user=applicant).all()
        assert len(applicant_notifications) == 1
        assert isinstance(applicant_notifications[0].details, MembershipRefusedNotificationDetails)
        assert applicant_notifications[0].details.organization == org

        admin_notifications = Notification.objects(user=admin).all()
        assert len(admin_notifications) == 1
        assert admin_notifications[0].handled_at is not None

        # Step 3: Applicant sends a new request after refusal
        second_request = MembershipRequest(user=applicant, comment="Please reconsider")
        org.add_membership_request(second_request)

        org.reload()
        assert len(org.pending_requests) == 1
        assert org.pending_requests[0].comment == "Please reconsider"
        assert org.pending_requests[0].id != first_request.id

        admin_pending_notifications = Notification.objects(user=admin, handled_at=None).all()
        assert len(admin_pending_notifications) == 1
        assert admin_pending_notifications[0].details.request_user == applicant

        # Step 4: Admin accepts the second request
        second_request = org.pending_requests[0]
        second_request.status = "accepted"
        second_request.handled_by = admin
        second_request.handled_on = datetime.utcnow()
        member = Member(user=applicant, role="editor")
        org.members.append(member)
        org.save()
        MembershipRequest.after_handle.send(second_request, org=org)
        notify_membership_response(org.id, str(second_request.id))

        org.reload()
        assert len(org.pending_requests) == 0
        assert len(org.accepted_requests) == 1
        assert org.is_member(applicant)

        # Verify applicant received an acceptance notification
        applicant_notifications = Notification.objects(user=applicant).all()
        assert len(applicant_notifications) == 2

        acceptance_notifications = [
            n
            for n in applicant_notifications
            if isinstance(n.details, MembershipAcceptedNotificationDetails)
        ]
        assert len(acceptance_notifications) == 1
        assert acceptance_notifications[0].details.organization == org

        refusal_notifications = [
            n
            for n in applicant_notifications
            if isinstance(n.details, MembershipRefusedNotificationDetails)
        ]
        assert len(refusal_notifications) == 1

        # Verify all admin notifications are now handled
        admin_all_notifications = Notification.objects(user=admin).all()
        assert len(admin_all_notifications) == 2
        for notif in admin_all_notifications:
            assert notif.handled_at is not None
