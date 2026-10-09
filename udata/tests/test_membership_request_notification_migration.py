from mongoengine.connection import get_db

from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.db.migrations import load_migration
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.models import Notification
from udata.models import Member, MembershipRequest
from udata.tests.api import PytestOnlyDBTestCase


class CreateMembershipRequestNotificationsMigrationTest(PytestOnlyDBTestCase):
    def run_migration(self):
        load_migration("2025-10-31-create-membership-request-notifications.py").migrate(get_db())

    def test_a_pending_request_is_announced_to_the_admins(self):
        admin = UserFactory()
        applicant = UserFactory()
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin")],
            requests=[MembershipRequest(user=applicant, comment="Let me in")],
        )

        self.run_migration()

        notifications = Notification.objects(user=admin)
        assert notifications.count() == 1
        assert notifications.first().type == NotificationType.ORGANIZATION_MEMBERSHIP_REQUESTED
        assert notifications.first().details.request_organization == organization
        assert notifications.first().details.request_user == applicant

    def test_a_pending_invitation_is_left_to_the_invitee(self):
        """An invitation is answered by the invited user, so the admins this migration
        notifies have nothing to do with it."""
        admin = UserFactory()
        invited = UserFactory()
        OrganizationFactory(
            members=[Member(user=admin, role="admin")],
            requests=[MembershipRequest(kind="invitation", user=invited, created_by=admin)],
        )

        self.run_migration()

        assert Notification.objects.count() == 0
