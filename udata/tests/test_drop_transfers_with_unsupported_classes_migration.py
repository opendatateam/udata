from mongoengine.connection import get_db

from udata.core.dataset.factories import DatasetFactory, LicenseFactory
from udata.core.user.factories import UserFactory
from udata.db import migrations
from udata.features.transfer.factories import TransferFactory
from udata.features.transfer.models import Transfer
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-09-07-drop-transfers-with-unsupported-classes.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def transfer_pointing_at_a_license(field):
    """A transfer as the API could create them before `Transfer` got its `choices`:
    written past validation, since the model now refuses it."""
    owner = UserFactory()
    transfer = TransferFactory(
        owner=owner, recipient=UserFactory(), subject=DatasetFactory(owner=owner)
    )
    Transfer._get_collection().update_one(
        {"_id": transfer.id},
        {"$set": {field: {"_cls": "License", "_ref": LicenseFactory().to_dbref()}}},
    )
    return transfer


class DropTransfersWithUnsupportedClassesMigrationTest(PytestOnlyDBTestCase):
    def test_transfers_with_an_unsupported_class_are_dropped(self):
        transfers = [
            transfer_pointing_at_a_license(field) for field in ("subject", "recipient", "owner")
        ]

        migrate()

        assert Transfer.objects(id__in=[t.id for t in transfers]).count() == 0

    def test_regular_transfers_are_kept(self):
        owner = UserFactory()
        transfer = TransferFactory(
            owner=owner, recipient=UserFactory(), subject=DatasetFactory(owner=owner)
        )

        migrate()

        assert Transfer.objects(id=transfer.id).count() == 1
