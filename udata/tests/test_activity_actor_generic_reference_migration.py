from bson import DBRef
from mongoengine.connection import get_db

from udata.core.dataset.activities import UserCreatedDataset
from udata.core.dataset.factories import DatasetFactory
from udata.core.user.factories import UserFactory
from udata.db import migrations
from udata.models import Activity
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-09-17-activity-actor-to-generic-reference.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def store_actor_as_object_id(activity):
    """Rewrite the stored actor the way `ReferenceField("User")` used to."""
    get_db().activity.update_one({"_id": activity.id}, {"$set": {"actor": activity.actor.id}})


class ActivityActorGenericReferenceMigrationTest(PytestOnlyDBTestCase):
    def test_bare_object_id_actors_become_generic_references(self):
        user = UserFactory()
        activity = UserCreatedDataset.objects.create(actor=user, related_to=DatasetFactory())
        store_actor_as_object_id(activity)

        migrate()

        assert get_db().activity.find_one({"_id": activity.id})["actor"] == {
            "_cls": "User",
            "_ref": DBRef("user", user.id),
        }
        assert Activity.objects.get(id=activity.id).actor == user

    def test_already_converted_actors_are_left_alone(self):
        user = UserFactory()
        activity = UserCreatedDataset.objects.create(actor=user, related_to=DatasetFactory())

        migrate()

        assert Activity.objects.get(id=activity.id).actor == user

    def test_every_activity_is_converted_across_batches(self):
        """The conversion is batched: it must not stop at the first batch."""
        user = UserFactory()
        dataset = DatasetFactory()
        activities = [
            UserCreatedDataset.objects.create(actor=user, related_to=dataset) for _ in range(5)
        ]
        for activity in activities:
            store_actor_as_object_id(activity)

        # A fresh module per `get()`, so shrinking the batch stays local to this test.
        migration = migrations.get(MIGRATION)
        migration.module.BATCH_SIZE = 2
        migration.migrate(get_db())

        assert get_db().activity.count_documents({"actor": {"$type": "objectId"}}) == 0
