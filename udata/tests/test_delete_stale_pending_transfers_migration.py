from mongoengine.connection import get_db

from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.db import migrations
from udata.features.notifications.models import Notification
from udata.features.transfer.factories import TransferFactory
from udata.features.transfer.models import Transfer
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-11-02-delete-stale-pending-transfers.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


class DeleteStalePendingTransfersMigrationTest(PytestOnlyDBTestCase):
    def test_pending_transfer_of_a_former_owner_is_deleted(self):
        former_owner = UserFactory()
        recipient_admin = UserFactory()
        dataset = DatasetFactory(owner=former_owner)
        transfer = TransferFactory(
            owner=former_owner,
            recipient=OrganizationFactory(admins=[recipient_admin]),
            subject=dataset,
        )
        # As accepting another transfer did until now: the owner changes, the transfer stays.
        Dataset._get_collection().update_one(
            {"_id": dataset.id}, {"$set": {"owner": UserFactory().id}}
        )

        migrate()

        assert Transfer.objects(id=transfer.id).count() == 0
        assert Notification.objects(user=recipient_admin).count() == 0

    def test_pending_transfer_of_the_current_owner_is_kept(self):
        owner = OrganizationFactory()
        transfer = TransferFactory(
            owner=owner, recipient=UserFactory(), subject=DatasetFactory(organization=owner)
        )

        migrate()

        assert Transfer.objects(id=transfer.id).count() == 1

    def test_answered_transfer_of_a_former_owner_is_kept(self):
        former_owner = UserFactory()
        recipient = UserFactory()
        transfer = TransferFactory(
            owner=former_owner,
            recipient=recipient,
            subject=DatasetFactory(owner=recipient),
            status="accepted",
        )

        migrate()

        assert Transfer.objects(id=transfer.id).count() == 1
