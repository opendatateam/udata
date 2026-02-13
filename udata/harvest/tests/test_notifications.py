from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.features.notifications.models import Notification
from udata.harvest.models import VALIDATION_ACCEPTED, VALIDATION_PENDING, VALIDATION_REFUSED
from udata.harvest.notifications import (
    ValidateHarvesterNotificationDetails,
    validate_harvester_notifications,
)
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.helpers import assert_equal_dates

from .. import actions
from .factories import HarvestSourceFactory, MockBackendsMixin


class HarvestNotificationsTest(MockBackendsMixin, PytestOnlyDBTestCase):
    def test_pending_harvester_validations(self):
        source = HarvestSourceFactory()
        admin = AdminFactory()
        user = UserFactory()

        assert len(validate_harvester_notifications(user)) == 0

        notifications = validate_harvester_notifications(admin)

        assert len(notifications) == 1
        dt, details = notifications[0]
        assert_equal_dates(dt, source.created_at)
        assert details["id"] == source.id
        assert details["name"] == source.name

    def test_create_source_creates_notification_for_admins(self):
        admin1 = AdminFactory()
        admin2 = AdminFactory()
        user = UserFactory()

        source = actions.create_source(
            name="Test Source",
            url="http://example.com",
            backend="dcat",
        )

        # Admins should receive notifications
        admin1_notifications = Notification.objects(user=admin1)
        assert admin1_notifications.count() == 1
        assert isinstance(admin1_notifications[0].details, ValidateHarvesterNotificationDetails)
        assert admin1_notifications[0].details.source == source
        assert admin1_notifications[0].details.status == VALIDATION_PENDING

        admin2_notifications = Notification.objects(user=admin2)
        assert admin2_notifications.count() == 1

        # Regular user should not receive notifications
        user_notifications = Notification.objects(user=user)
        assert user_notifications.count() == 0

    def test_create_source_does_not_duplicate_notifications(self):
        admin = AdminFactory()

        source = actions.create_source(
            name="Test Source",
            url="http://example.com",
            backend="dcat",
        )

        # Manually trigger the signal again (simulating duplicate call)
        from udata.harvest.signals import harvest_source_created

        harvest_source_created.send(source)

        # Should still only have one notification
        notifications = Notification.objects(user=admin)
        assert notifications.count() == 1

    def test_validate_source_creates_notification_for_owner(self):
        owner = UserFactory()
        source = HarvestSourceFactory(owner=owner)

        actions.validate_source(source)

        notifications = Notification.objects(user=owner)
        assert notifications.count() == 1
        assert isinstance(notifications[0].details, ValidateHarvesterNotificationDetails)
        assert notifications[0].details.source == source
        assert notifications[0].details.status == VALIDATION_ACCEPTED

    def test_validate_source_creates_notification_for_org_admins(self):
        org_admin = UserFactory()
        org_member = UserFactory()
        org = OrganizationFactory(
            members=[
                {"user": org_admin, "role": "admin"},
                {"user": org_member, "role": "editor"},
            ]
        )
        source = HarvestSourceFactory(organization=org)

        actions.validate_source(source)

        # Org admin should receive notification
        admin_notifications = Notification.objects(user=org_admin)
        assert admin_notifications.count() == 1
        assert admin_notifications[0].details.status == VALIDATION_ACCEPTED

        # Org editor should not receive notification
        member_notifications = Notification.objects(user=org_member)
        assert member_notifications.count() == 0

    def test_refuse_source_creates_notification_for_owner(self):
        owner = UserFactory()
        source = HarvestSourceFactory(owner=owner)

        actions.reject_source(source, comment="Invalid source")

        notifications = Notification.objects(user=owner)
        assert notifications.count() == 1
        assert isinstance(notifications[0].details, ValidateHarvesterNotificationDetails)
        assert notifications[0].details.source == source
        assert notifications[0].details.status == VALIDATION_REFUSED

    def test_refuse_source_creates_notification_for_org_admins(self):
        org_admin = UserFactory()
        org = OrganizationFactory(members=[{"user": org_admin, "role": "admin"}])
        source = HarvestSourceFactory(organization=org)

        actions.reject_source(source, comment="Invalid source")

        notifications = Notification.objects(user=org_admin)
        assert notifications.count() == 1
        assert notifications[0].details.status == VALIDATION_REFUSED
