from mongoengine.connection import get_db

from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.notifications import MembershipRequestNotificationDetails
from udata.core.user.factories import UserFactory
from udata.db import migrations
from udata.features.notifications.models import Notification
from udata.models import Member, MembershipRequest
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-10-01-delete-pending-requests-of-members.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


class DeletePendingRequestsOfMembersMigrationTest(PytestOnlyDBTestCase):
    def test_pending_invitation_and_request_of_a_member_are_deleted(self):
        user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=user, role="editor")],
            requests=[
                MembershipRequest(kind="invitation", user=user, role="admin"),
                MembershipRequest(user=user, comment="Please add me"),
            ],
        )

        migrate()

        organization.reload()
        assert organization.requests == []

    def test_pending_email_invitation_to_a_member_address_is_deleted(self):
        user = UserFactory(email="John.Doe@example.com")
        organization = OrganizationFactory(
            members=[Member(user=user, role="editor")],
            requests=[MembershipRequest(kind="invitation", email="john.doe@example.com")],
        )

        migrate()

        organization.reload()
        assert organization.requests == []

    def test_handled_requests_of_a_member_are_kept(self):
        user = UserFactory()
        handled = MembershipRequest(user=user, comment="Please add me", status="accepted")
        organization = OrganizationFactory(
            members=[Member(user=user, role="editor")], requests=[handled]
        )

        migrate()

        organization.reload()
        assert [r.id for r in organization.requests] == [handled.id]

    def test_pending_requests_of_non_members_are_kept(self):
        member = UserFactory()
        requests = [
            MembershipRequest(kind="invitation", user=UserFactory()),
            MembershipRequest(kind="invitation", email="someone@example.com"),
            MembershipRequest(user=UserFactory(), comment="Please add me"),
        ]
        organization = OrganizationFactory(
            members=[Member(user=member, role="admin")], requests=requests
        )

        migrate()

        organization.reload()
        assert [r.id for r in organization.requests] == [r.id for r in requests]
        assert [r.status for r in organization.requests] == ["pending"] * 3

    def test_member_listed_twice_is_kept_once_with_its_first_role(self):
        admin = UserFactory()
        user = UserFactory()
        organization = OrganizationFactory(
            members=[
                Member(user=admin, role="admin"),
                Member(user=user, role="editor"),
                Member(user=user, role="admin"),
            ]
        )

        migrate()

        organization.reload()
        assert [(m.user, m.role) for m in organization.members] == [
            (admin, "admin"),
            (user, "editor"),
        ]
        assert organization.metrics["members"] == 2

    def test_notification_of_a_deleted_request_is_handled(self):
        admin = UserFactory()
        user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin"), Member(user=user, role="editor")],
            requests=[MembershipRequest(user=user, comment="Please add me")],
        )
        notification = Notification(
            user=admin,
            details=MembershipRequestNotificationDetails(
                request_organization=organization, request_user=user
            ),
        )
        notification.save()

        migrate()

        notification.reload()
        assert notification.handled_at is not None
