from datetime import UTC, datetime

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataservices.notifications import DataserviceCreatedNotificationDetails
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.features.notifications.models import Notification
from udata.tests.api import PytestOnlyDBTestCase


class DataserviceNotificationsTest(PytestOnlyDBTestCase):
    def test_dataservice_creation_notifies_dataset_owner_user(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        dataservice = DataserviceFactory(datasets=[dataset])
        notifications = Notification.objects(user=owner, handled_at=None)
        assert notifications.count() == 1
        assert notifications[0].details.dataservice == dataservice
        assert notifications[0].details.dataset == dataset
        assert isinstance(notifications[0].details, DataserviceCreatedNotificationDetails)

    def test_dataservice_creation_notifies_dataset_org_admins(self):
        admin1 = UserFactory()
        admin2 = UserFactory()
        org = OrganizationFactory(
            members=[
                {"user": admin1, "role": "admin"},
                {"user": admin2, "role": "admin"},
            ]
        )
        dataset = DatasetFactory(organization=org)
        dataservice = DataserviceFactory(datasets=[dataset])
        assert dataservice.id is not None
        assert Notification.objects(user=admin1, handled_at=None).count() == 1
        assert Notification.objects(user=admin2, handled_at=None).count() == 1

    def test_dataservice_creation_no_notification_for_non_owner(self):
        owner = UserFactory()
        other_user = UserFactory()
        dataset = DatasetFactory(owner=owner)
        dataservice = DataserviceFactory(datasets=[dataset])
        assert dataservice.id is not None
        assert Notification.objects(user=other_user).count() == 0

    def test_dataservice_deletion_cleans_notifications(self):
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        dataservice = DataserviceFactory(datasets=[dataset])
        notification = Notification.objects(user=owner).first()
        assert notification is not None
        dataservice.deleted_at = datetime.now(UTC)
        dataservice.save()
        assert Notification.objects(id=notification.id).count() == 0

    def test_dataservice_creation_no_notifications_when_no_datasets(self):
        """No notifications are created when dataservice has no datasets"""
        DataserviceFactory(datasets=[])
        assert Notification.objects.count() == 0

    def test_dataservice_creation_notifies_for_multiple_datasets(self):
        """Notifications are created for each dataset's responsible users"""
        owner1 = UserFactory()
        owner2 = UserFactory()
        dataset1 = DatasetFactory(owner=owner1)
        dataset2 = DatasetFactory(owner=owner2)
        dataservice = DataserviceFactory(datasets=[dataset1, dataset2])

        # Each dataset owner should receive a notification
        assert Notification.objects(user=owner1, handled_at=None).count() == 1
        assert Notification.objects(user=owner2, handled_at=None).count() == 1

        # Verify the notifications reference the correct datasets
        notif1 = Notification.objects(user=owner1).first()
        assert notif1.details.dataset == dataset1
        assert notif1.details.dataservice == dataservice

        notif2 = Notification.objects(user=owner2).first()
        assert notif2.details.dataset == dataset2
        assert notif2.details.dataservice == dataservice

    def test_dataservice_deletion_cleans_all_related_notifications(self):
        """All notifications for a dataservice are cleaned up on deletion"""
        owner1 = UserFactory()
        owner2 = UserFactory()
        dataset1 = DatasetFactory(owner=owner1)
        dataset2 = DatasetFactory(owner=owner2)
        dataservice = DataserviceFactory(datasets=[dataset1, dataset2])

        # Should have 2 notifications (one for each dataset owner)
        assert Notification.objects.count() == 2

        # Delete the dataservice
        dataservice.deleted_at = datetime.now(UTC)
        dataservice.save()

        # All notifications should be cleaned up
        assert Notification.objects.count() == 0
