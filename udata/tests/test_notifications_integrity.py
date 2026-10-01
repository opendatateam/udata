from datetime import UTC, datetime

import pytest
from mongoengine import ValidationError

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.notifications import DataserviceCreatedNotificationDetails
from udata.core.dataset.factories import DatasetFactory
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.discussions.notifications import DiscussionNotificationDetails
from udata.core.reuse.factories import ReuseFactory
from udata.core.reuse.notifications import ReuseCreatedNotificationDetails
from udata.core.user.factories import AdminFactory, UserFactory
from udata.features.notifications.constants import NotificationType
from udata.features.notifications.models import DETAILS_BY_TYPE, Notification
from udata.features.transfer.factories import TransferFactory
from udata.harvest.actions import delete_source, purge_sources
from udata.harvest.notifications import ValidateHarvesterNotificationDetails
from udata.harvest.tests.factories import HarvestSourceFactory
from udata.tests.api import PytestOnlyDBTestCase


class NotificationIntegrityTest(PytestOnlyDBTestCase):
    """Test notification cleanup when referenced documents are deleted."""

    def test_discussion_notification_cleanup_on_discussion_delete(self):
        """Test that notifications are cleaned up when a discussion is deleted."""
        # Create a user and discussion with messages
        user = UserFactory()
        dataset = DatasetFactory()
        from udata.core.discussions.factories import MessageDiscussionFactory

        message = MessageDiscussionFactory(posted_by=user)
        discussion = DiscussionFactory(user=user, subject=dataset, discussion=[message])

        # Create a notification for this discussion
        notification = Notification(
            user=user,
            type=NotificationType.DISCUSSION_NEW,
            details=DiscussionNotificationDetails(
                discussion=discussion,
                message_id=discussion.discussion[0].id,
            ),
        )
        notification.save()

        # Verify notification exists
        assert Notification.objects.count() == 1
        assert Notification.objects.first().details.discussion == discussion

        # Delete the discussion
        discussion.delete()

        # Verify notification is cleaned up
        assert Notification.objects.count() == 0

    def test_transfer_notification_cleanup_on_transfer_delete(self):
        """Test that notifications are cleaned up when a transfer is deleted."""
        # Create users and organization
        owner = UserFactory()
        recipient = UserFactory()
        dataset = DatasetFactory(owner=owner)

        # Create a transfer (this automatically creates a notification via signal)
        transfer = TransferFactory(
            user=owner, owner=owner, recipient=recipient, subject=dataset, status="pending"
        )

        # Verify notification exists (automatically created by factory)
        assert Notification.objects.count() == 1
        notification = Notification.objects.first()
        assert notification.user == recipient

        # Delete the transfer
        transfer.delete()

        # Verify notification is cleaned up
        assert Notification.objects.count() == 0

    def test_harvest_source_notification_cleanup_on_source_delete(self):
        """Test that notifications are cleaned up when a harvest source is deleted."""
        # The source is created first: creating one notifies every existing sysadmin,
        # which would add a notification on top of the one this test creates.
        source = HarvestSourceFactory()
        admin = AdminFactory()

        # Create a notification for this harvest source
        notification = Notification(
            user=admin,
            type=NotificationType.HARVEST_SOURCE_PENDING,
            details=ValidateHarvesterNotificationDetails(source=source),
        )
        notification.save()

        # Verify notification exists
        assert Notification.objects.count() == 1

        # Delete the harvest source
        delete_source(source)

        # Verify notification is cleaned up (via signal)
        assert Notification.objects.count() == 0

    def test_harvest_source_notification_cleanup_on_source_purge(self):
        """Test that notifications are cleaned up when a harvest source is purged."""
        # The source is created first: creating one notifies every existing sysadmin,
        # which would add a notification on top of the one this test creates.
        source = HarvestSourceFactory()
        admin = AdminFactory()

        # Create a notification for this harvest source
        notification = Notification(
            user=admin,
            type=NotificationType.HARVEST_SOURCE_PENDING,
            details=ValidateHarvesterNotificationDetails(source=source),
        )
        notification.save()

        # Verify notification exists
        assert Notification.objects.count() == 1

        # Mark source as deleted and purge it
        delete_source(source)
        purge_sources()

        # Verify notification is cleaned up (via purge function)
        assert Notification.objects.count() == 0

    def test_multiple_notifications_cleanup(self):
        """Test that multiple notifications are cleaned up correctly."""
        # Create users and discussions
        user1 = UserFactory()
        user2 = UserFactory()
        dataset = DatasetFactory()
        message1 = MessageDiscussionFactory(posted_by=user1)
        message2 = MessageDiscussionFactory(posted_by=user2)
        discussion1 = DiscussionFactory(user=user1, subject=dataset, discussion=[message1])
        discussion2 = DiscussionFactory(user=user2, subject=dataset, discussion=[message2])

        # Create notifications for both discussions
        notification1 = Notification(
            user=user1,
            type=NotificationType.DISCUSSION_NEW,
            details=DiscussionNotificationDetails(
                discussion=discussion1,
                message_id=discussion1.discussion[0].id,
            ),
        )
        notification1.save()

        notification2 = Notification(
            user=user2,
            type=NotificationType.DISCUSSION_NEW,
            details=DiscussionNotificationDetails(
                discussion=discussion2,
                message_id=discussion2.discussion[0].id,
            ),
        )
        notification2.save()

        # Verify both notifications exist
        assert Notification.objects.count() == 2

        # Delete one discussion
        discussion1.delete()

        # Verify only one notification is cleaned up
        assert Notification.objects.count() == 1
        assert Notification.objects.first().details.discussion == discussion2

        # Delete the second discussion
        discussion2.delete()

        # Verify all notifications are cleaned up
        assert Notification.objects.count() == 0

    def test_dataservice_notification_cleanup_on_dataservice_delete(self):
        """Test that notifications are cleaned up when a dataservice is deleted."""
        # Create owner, dataset, and dataservice
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        dataservice = DataserviceFactory(datasets=[dataset])

        # Verify notification was created (via signal on dataservice creation)
        assert Notification.objects.count() == 1
        notification = Notification.objects.first()
        assert notification.user == owner
        assert notification.details.dataservice == dataservice

        # Delete the dataservice
        dataservice.deleted_at = datetime.now(UTC)
        dataservice.save()

        # Verify notification is cleaned up (via signal)
        assert Notification.objects.count() == 0

    def test_reuse_notification_cleanup_on_reuse_delete(self):
        """Test that notifications are cleaned up when a reuse is deleted."""
        # Create owner, dataset, and reuse
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        reuse = ReuseFactory(datasets=[dataset])

        # Verify notification was created (via signal on reuse creation)
        assert Notification.objects.count() == 1
        notification = Notification.objects.first()
        assert notification.user == owner
        assert notification.details.reuse == reuse

        # Delete the reuse
        reuse.deleted = datetime.now(UTC)
        reuse.save()

        # Verify notification is cleaned up (via signal)
        assert Notification.objects.count() == 0

    def test_discussion_notification_survives_message_delete(self):
        """Test that notifications are not broken when referenced messages are deleted."""
        user = UserFactory()
        dataset = DatasetFactory()
        message1 = MessageDiscussionFactory(posted_by=user)
        message2 = MessageDiscussionFactory(posted_by=user)
        discussion = DiscussionFactory(user=user, subject=dataset, discussion=[message1, message2])

        notification = Notification(
            user=user,
            type=NotificationType.DISCUSSION_COMMENT,
            details=DiscussionNotificationDetails(
                discussion=discussion,
                message_id=discussion.discussion[1].id,
            ),
        )
        notification.save()

        assert Notification.objects.count() == 1
        assert Notification.objects.first().details.discussion == discussion

        discussion.remove_message(message2.id)

        assert Notification.objects.count() == 0

    def test_reuse_notification_cleanup_on_dataset_delete(self):
        """Test that reuse notifications are cleaned up when a referenced dataset is deleted."""
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        ReuseFactory(datasets=[dataset])

        assert Notification.objects.count() == 1
        notification = Notification.objects.first()
        assert isinstance(notification.details, ReuseCreatedNotificationDetails)
        assert notification.details.dataset == dataset

        # Soft-delete the dataset; this should trigger cleanup of the notification.
        dataset.deleted = datetime.now(UTC)
        dataset.save()

        assert Notification.objects.count() == 0

    def test_every_type_declares_the_details_it_carries(self):
        """A type the front receives must always come with the same payload shape."""
        assert set(DETAILS_BY_TYPE) == set(NotificationType)

    def test_saving_a_type_with_foreign_details_is_rejected(self):
        notification = Notification(
            user=UserFactory(),
            type=NotificationType.DISCUSSION_NEW,
            details=ReuseCreatedNotificationDetails(reuse=ReuseFactory()),
        )

        with pytest.raises(ValidationError):
            notification.save()

    def test_dataservice_notification_cleanup_on_dataset_delete(self):
        """Test that dataservice notifications are cleaned up when a referenced dataset is deleted."""
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)
        DataserviceFactory(datasets=[dataset])

        assert Notification.objects.count() == 1
        notification = Notification.objects.first()
        assert isinstance(notification.details, DataserviceCreatedNotificationDetails)
        assert notification.details.dataset == dataset

        # Soft-delete the dataset; this should trigger cleanup of the notification.
        dataset.deleted = datetime.now(UTC)
        dataset.save()

        assert Notification.objects.count() == 0
