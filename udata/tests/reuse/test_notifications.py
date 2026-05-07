from datetime import UTC, datetime

from udata.core.dataservices.models import (
    Dataservice,  # noqa: F401 - Register Dataservice for Reuse model reference
)
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.reuse.notifications import ReuseCreatedNotificationDetails
from udata.core.user.factories import UserFactory
from udata.features.notifications.models import Notification
from udata.tests.api import PytestOnlyDBTestCase


class ReuseNotificationsTest(PytestOnlyDBTestCase):
    def test_reuse_creation_notifies_dataset_owner_user(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        reuse = ReuseFactory(datasets=[dataset])
        notifications = Notification.objects(user=owner, handled_at=None)
        assert notifications.count() == 1
        assert notifications[0].details.reuse == reuse
        assert notifications[0].details.dataset == dataset
        assert isinstance(notifications[0].details, ReuseCreatedNotificationDetails)

    def test_reuse_creation_notifies_dataset_org_admins(self):
        admin1 = UserFactory()
        admin2 = UserFactory()
        org = OrganizationFactory(members=[
            {"user": admin1, "role": "admin"},
            {"user": admin2, "role": "admin"},
        ])
        dataset = DatasetFactory(organization=org)
        reuse = ReuseFactory(datasets=[dataset])
        assert reuse.id is not None
        assert Notification.objects(user=admin1, handled_at=None).count() == 1
        assert Notification.objects(user=admin2, handled_at=None).count() == 1

    def test_reuse_creation_no_notification_for_non_owner(self):
        owner = UserFactory()
        other_user = UserFactory()
        dataset = DatasetFactory(owner=owner)
        reuse = ReuseFactory(datasets=[dataset])
        assert reuse.id is not None
        assert Notification.objects(user=other_user).count() == 0

    def test_reuse_deletion_cleans_notifications(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        reuse = ReuseFactory(datasets=[dataset])
        notification = Notification.objects(user=owner).first()
        assert notification is not None
        reuse.deleted = datetime.now(UTC)
        reuse.save()
        assert Notification.objects(id=notification.id).count() == 0

    def test_reuse_creation_no_notifications_when_no_datasets(self):
        """No notifications are created when reuse has no datasets"""
        ReuseFactory(datasets=[])
        assert Notification.objects.count() == 0

    def test_reuse_creation_notifies_for_multiple_datasets(self):
        """Notifications are created for each dataset's responsible users"""
        owner1 = UserFactory()
        owner2 = UserFactory()
        dataset1 = DatasetFactory(owner=owner1)
        dataset2 = DatasetFactory(owner=owner2)
        reuse = ReuseFactory(datasets=[dataset1, dataset2])
        
        # Each dataset owner should receive a notification
        assert Notification.objects(user=owner1, handled_at=None).count() == 1
        assert Notification.objects(user=owner2, handled_at=None).count() == 1
        
        # Verify the notifications reference the correct datasets
        notif1 = Notification.objects(user=owner1).first()
        assert notif1.details.dataset == dataset1
        assert notif1.details.reuse == reuse
        
        notif2 = Notification.objects(user=owner2).first()
        assert notif2.details.dataset == dataset2
        assert notif2.details.reuse == reuse

    def test_reuse_deletion_cleans_all_related_notifications(self):
        """All notifications for a reuse are cleaned up on deletion"""
        owner1 = UserFactory()
        owner2 = UserFactory()
        dataset1 = DatasetFactory(owner=owner1)
        dataset2 = DatasetFactory(owner=owner2)
        reuse = ReuseFactory(datasets=[dataset1, dataset2])
        
        # Should have 2 notifications (one for each dataset owner)
        assert Notification.objects.count() == 2
        
        # Delete the reuse
        reuse.deleted = datetime.now(UTC)
        reuse.save()
        
        # All notifications should be cleaned up
        assert Notification.objects.count() == 0
