from datetime import UTC, datetime

from mongoengine.connection import get_db

from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.notifications import MembershipRequestNotificationDetails
from udata.core.user.factories import UserFactory
from udata.db import migrations
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.models import Notification
from udata.models import Member, MembershipRequest
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-10-15-remove-deleted-users-membership-requests.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def notify(recipient, organization, user, kind):
    notification = Notification(
        user=recipient,
        type=(
            NotificationType.ORGANIZATION_MEMBERSHIP_INVITED
            if kind == "invitation"
            else NotificationType.ORGANIZATION_MEMBERSHIP_REQUESTED
        ),
        details=MembershipRequestNotificationDetails(
            request_organization=organization, request_user=user
        ),
    )
    notification.save()
    return notification


class RemoveDeletedUsersMembershipRequestsMigrationTest(PytestOnlyDBTestCase):
    def test_pending_request_and_invitation_of_deleted_user_are_removed(self):
        user_a = UserFactory()
        user_b = UserFactory()
        admin = UserFactory()
        refused = MembershipRequest(user=user_a, comment="Please add me", status="refused")
        pending_b = MembershipRequest(user=user_b, comment="Please add me too")
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin")],
            requests=[
                MembershipRequest(user=user_a, comment="Please add me"),
                refused,
                pending_b,
            ],
        )
        # An account can only have one pending entry per organization, so the
        # invitation lives in another one.
        inviting_organization = OrganizationFactory(
            requests=[MembershipRequest(kind="invitation", user=user_a, role="editor")]
        )
        # Simulate an account deleted before the `mark_as_deleted` fix: flag it directly,
        # calling `mark_as_deleted` would remove the pending requests itself.
        user_a.deleted = datetime.now(UTC)
        user_a.save()

        migrate()

        organization.reload()
        assert [r.id for r in organization.requests] == [refused.id, pending_b.id]
        assert [r.status for r in organization.requests] == ["refused", "pending"]
        inviting_organization.reload()
        assert inviting_organization.requests == []

    def test_notifications_about_deleted_user_are_removed(self):
        admin = UserFactory()
        user_a = UserFactory()
        user_b = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin")],
            requests=[MembershipRequest(user=user_a, comment="Please add me")],
        )
        # An account can only have one pending entry per organization, so the
        # invitation lives in another one.
        inviting_organization = OrganizationFactory(
            requests=[MembershipRequest(kind="invitation", user=user_a, role="editor")]
        )
        request_notification = notify(admin, organization, user_a, "request")
        invitation_notification = notify(admin, inviting_organization, user_a, "invitation")
        surviving_notification = notify(admin, organization, user_b, "request")
        user_a.deleted = datetime.now(UTC)
        user_a.save()

        migrate()

        assert Notification.objects(id=request_notification.id).first() is None
        assert Notification.objects(id=invitation_notification.id).first() is None
        surviving_notification.reload()
        assert surviving_notification.handled_at is None

    def test_email_only_invitation_is_kept(self):
        user_a = UserFactory()
        organization = OrganizationFactory(
            requests=[
                MembershipRequest(user=user_a, comment="Please add me"),
                MembershipRequest(kind="invitation", email="someone@example.com"),
            ]
        )
        user_a.deleted = datetime.now(UTC)
        user_a.save()

        migrate()

        organization.reload()
        assert len(organization.requests) == 1
        assert organization.requests[0].email == "someone@example.com"

    def test_running_twice_gives_the_same_result(self):
        admin = UserFactory()
        user_a = UserFactory()
        user_b = UserFactory()
        pending_b = MembershipRequest(user=user_b, comment="Please add me too")
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin")],
            requests=[
                MembershipRequest(user=user_a, comment="Please add me"),
                pending_b,
            ],
        )
        notification = notify(admin, organization, user_a, "request")
        surviving_notification = notify(admin, organization, user_b, "request")
        user_a.deleted = datetime.now(UTC)
        user_a.save()

        migrate()
        organization.reload()
        first_requests = [r.id for r in organization.requests]
        assert Notification.objects(id=notification.id).first() is None

        migrate()

        organization.reload()
        assert [r.id for r in organization.requests] == first_requests == [pending_b.id]
        assert Notification.objects(id=surviving_notification.id).count() == 1
