from datetime import UTC, datetime

from mongoengine.connection import get_db

from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.notifications import MembershipRequestNotificationDetails
from udata.core.user.factories import UserFactory
from udata.core.user.models import User
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
    def test_pending_requests_of_deleted_user_are_removed(self):
        user_a = UserFactory()
        user_b = UserFactory()
        admin = UserFactory()
        refused = MembershipRequest(user=user_a, comment="Please add me", status="refused")
        pending_b = MembershipRequest(user=user_b, comment="Please add me too")
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin")],
            requests=[
                MembershipRequest(user=user_a, comment="Please add me"),
                MembershipRequest(kind="invitation", user=user_a, role="editor"),
                refused,
                pending_b,
            ],
        )
        # Simulate an account deleted before the `mark_as_deleted` fix: flag it directly,
        # calling `mark_as_deleted` would remove the pending requests itself.
        user_a.deleted = datetime.now(UTC)
        user_a.save()

        migrate()

        organization.reload()
        assert [r.id for r in organization.requests] == [refused.id, pending_b.id]
        assert [r.status for r in organization.requests] == ["refused", "pending"]

    def test_pending_request_of_removed_user_is_removed(self):
        user_c = UserFactory()
        organization = OrganizationFactory(
            requests=[MembershipRequest(user=user_c, comment="Please add me")]
        )
        # `User.delete` is overridden to raise: remove the document directly.
        User._get_collection().delete_one({"_id": user_c.id})

        migrate()

        organization.reload()
        assert organization.requests == []

    def test_notifications_of_removed_requests_are_marked_handled(self):
        admin = UserFactory()
        user_a = UserFactory()
        user_b = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin")],
            requests=[
                MembershipRequest(user=user_a, comment="Please add me"),
                MembershipRequest(kind="invitation", user=user_a, role="editor"),
                MembershipRequest(user=user_b, comment="Please add me too"),
            ],
        )
        request_notification = notify(admin, organization, user_a, "request")
        invitation_notification = notify(admin, organization, user_a, "invitation")
        surviving_notification = notify(admin, organization, user_b, "request")
        user_a.deleted = datetime.now(UTC)
        user_a.save()

        migrate()

        request_notification.reload()
        assert request_notification.handled_at is not None
        invitation_notification.reload()
        assert invitation_notification.handled_at is not None
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
        user_a.deleted = datetime.now(UTC)
        user_a.save()

        migrate()
        organization.reload()
        first_requests = [r.id for r in organization.requests]
        notification.reload()
        assert notification.handled_at is not None

        migrate()

        organization.reload()
        assert [r.id for r in organization.requests] == first_requests == [pending_b.id]
        notification.reload()
        assert notification.handled_at is not None
        assert Notification.objects(details__request_organization=organization).count() == 1
