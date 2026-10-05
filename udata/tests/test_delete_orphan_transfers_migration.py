from mongoengine.connection import get_db

from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.topic.factories import TopicFactory
from udata.core.topic.models import Topic
from udata.core.user.factories import UserFactory
from udata.db import migrations
from udata.features.notifications.models import Notification
from udata.features.transfer.factories import TransferFactory
from udata.features.transfer.models import Transfer
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-10-01-delete-orphan-transfers.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


class DeleteOrphanTransfersMigrationTest(PytestOnlyDBTestCase):
    def test_transfer_of_a_deleted_topic_is_deleted(self):
        owner = UserFactory()
        topic = TopicFactory(owner=owner)
        transfer = TransferFactory(owner=owner, recipient=UserFactory(), subject=topic)
        # As `Topic` deletion did until now: the transfer is left behind.
        Topic._get_collection().delete_one({"_id": topic.id})

        migrate()

        assert Transfer.objects(id=transfer.id).count() == 0

    def test_notification_of_a_purged_dataset_is_deleted(self):
        owner = UserFactory()
        recipient_admin = UserFactory()
        dataset = DatasetFactory(owner=owner)
        TransferFactory(
            owner=owner,
            recipient=OrganizationFactory(admins=[recipient_admin]),
            subject=dataset,
        )
        assert Notification.objects(user=recipient_admin).count() == 1
        # As the purges did until now: the transfer is gone, its notification is not.
        Transfer._get_collection().delete_many({})
        Dataset._get_collection().delete_one({"_id": dataset.id})

        migrate()

        assert Notification.objects(user=recipient_admin).count() == 0

    def test_transfers_and_notifications_of_live_documents_are_kept(self):
        owner = UserFactory()
        recipient_admin = UserFactory()
        transfer = TransferFactory(
            owner=owner,
            recipient=OrganizationFactory(admins=[recipient_admin]),
            subject=DatasetFactory(owner=owner),
        )

        migrate()

        assert Transfer.objects(id=transfer.id).count() == 1
        assert Notification.objects(user=recipient_admin).count() == 1
