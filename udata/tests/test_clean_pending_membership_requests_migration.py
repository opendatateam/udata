from mongoengine.connection import get_db

from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.notifications import MembershipRequestNotificationDetails
from udata.core.user.factories import UserFactory
from udata.db import migrations
from udata.features.notifications.models import Notification
from udata.models import Member, MembershipRequest
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-10-01-clean-pending-membership-requests.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def notify(recipient, organization, user, kind):
    notification = Notification(
        user=recipient,
        details=MembershipRequestNotificationDetails(
            request_organization=organization, request_user=user, kind=kind
        ),
    )
    notification.save()
    return notification


class CleanPendingMembershipRequestsMigrationTest(PytestOnlyDBTestCase):
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

    def test_pending_request_without_kind_of_a_member_is_deleted(self):
        """Requests created before invitations existed have no `kind` in the database."""
        admin = UserFactory()
        user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin"), Member(user=user, role="editor")],
            requests=[MembershipRequest(user=user, comment="Please add me")],
        )
        notification = notify(admin, organization, user, "request")
        get_db().organization.update_one(
            {"_id": organization.id}, {"$unset": {"requests.0.kind": ""}}
        )

        migrate()

        organization.reload()
        assert organization.requests == []
        notification.reload()
        assert notification.handled_at is not None

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

    def test_single_pending_entry_of_non_members_is_kept(self):
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

    def test_email_invitation_is_linked_to_the_account_of_its_address(self):
        user = UserFactory(email="John.Doe@example.com")
        organization = OrganizationFactory(
            requests=[MembershipRequest(kind="invitation", email="john.doe@example.com")]
        )

        migrate()

        organization.reload()
        assert organization.requests[0].user == user
        assert organization.requests[0].email is None
        notification = Notification.objects.get(user=user)
        assert notification.details.request_organization == organization
        assert notification.details.request_user == user
        assert notification.details.kind == "invitation"
        assert notification.handled_at is None
        assert notification.created_at == organization.requests[0].created

    def test_email_invitation_kept_over_a_request_of_the_same_user(self):
        """Same rule as `match_email_invitations`: the invitation carries the role an admin chose."""
        admin = UserFactory()
        user = UserFactory(email="John.Doe@example.com")
        invitation = MembershipRequest(
            kind="invitation", email="john.doe@example.com", role="partial_editor"
        )
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin")],
            requests=[MembershipRequest(user=user, comment="Please add me"), invitation],
        )
        request_notification = notify(admin, organization, user, "request")

        migrate()

        organization.reload()
        assert [r.id for r in organization.requests] == [invitation.id]
        assert organization.requests[0].user == user
        assert organization.requests[0].role == "partial_editor"
        request_notification.reload()
        assert request_notification.handled_at is not None
        assert Notification.objects(user=user, details__kind="invitation").count() == 1

    def test_invitation_kept_over_an_earlier_request_of_the_same_user(self):
        admin = UserFactory()
        user = UserFactory()
        invitation = MembershipRequest(kind="invitation", user=user, role="admin")
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin")],
            requests=[MembershipRequest(user=user, comment="Please add me"), invitation],
        )
        request_notification = notify(admin, organization, user, "request")
        invitation_notification = notify(user, organization, user, "invitation")

        migrate()

        organization.reload()
        assert [r.id for r in organization.requests] == [invitation.id]
        request_notification.reload()
        assert request_notification.handled_at is not None
        invitation_notification.reload()
        assert invitation_notification.handled_at is None

    def test_linked_invitation_kept_over_an_earlier_email_invitation_keeps_its_notification(self):
        user = UserFactory(email="John.Doe@example.com")
        invitation = MembershipRequest(kind="invitation", user=user)
        organization = OrganizationFactory(
            requests=[
                MembershipRequest(kind="invitation", email="john.doe@example.com"),
                invitation,
            ]
        )
        notification = notify(user, organization, user, "invitation")

        migrate()

        organization.reload()
        assert [r.id for r in organization.requests] == [invitation.id]
        assert [n.id for n in Notification.objects(user=user)] == [notification.id]
        notification.reload()
        assert notification.handled_at is None

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

    def test_only_notifications_of_deleted_requests_are_handled(self):
        admin = UserFactory()
        user = UserFactory()
        other = UserFactory()
        other_request = MembershipRequest(user=other, comment="Please add me too")
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin"), Member(user=user, role="editor")],
            requests=[MembershipRequest(user=user, comment="Please add me"), other_request],
        )
        notification = notify(admin, organization, user, "request")
        other_notification = notify(admin, organization, other, "request")

        migrate()

        notification.reload()
        assert notification.handled_at is not None
        other_notification.reload()
        assert other_notification.handled_at is None
        organization.reload()
        assert [r.id for r in organization.requests] == [other_request.id]

    def test_request_notification_without_kind_is_handled(self):
        """Request notifications created before invitations existed have no `kind`."""
        admin = UserFactory()
        user = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin"), Member(user=user, role="editor")],
            requests=[MembershipRequest(user=user, comment="Please add me")],
        )
        notification = notify(admin, organization, user, "request")
        Notification._get_collection().update_one(
            {"_id": notification.id}, {"$unset": {"details.kind": ""}}
        )

        migrate()

        notification.reload()
        assert notification.handled_at is not None
