from mongoengine.connection import get_db

from udata.core.activity.models import Activity, filter_by_actor_kinds
from udata.core.api_token.models import ApiToken
from udata.core.dataset.activities import UserCreatedDataset
from udata.core.dataset.factories import DatasetFactory
from udata.core.user.factories import UserFactory
from udata.db import migrations
from udata.harvest.tests.factories import HarvestSourceFactory
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-11-10-index-activity-actor-kind.py"


def used_indexes(plan: dict) -> set[str]:
    """The names of the indexes a query plan scans, at any depth."""
    names = {plan["indexName"]} if plan.get("stage") == "IXSCAN" else set()
    for key in ("inputStage", "queryPlan"):
        if key in plan:
            names |= used_indexes(plan[key])
    for child in plan.get("inputStages", []):
        names |= used_indexes(child)
    return names


class ActivityActorKindIndexMigrationTest(PytestOnlyDBTestCase):
    def test_the_actor_kind_filter_uses_the_index(self):
        # A few activities of the kinds filtered on among many of users, as in production:
        # on an empty collection every plan ties and nothing tells the index apart.
        user, dataset = UserFactory(), DatasetFactory()
        for _ in range(50):
            UserCreatedDataset.objects.create(actor=user, related_to=dataset)
        by_harvest = UserCreatedDataset.objects.create(
            actor=HarvestSourceFactory(), related_to=dataset
        )
        by_token = UserCreatedDataset.objects.create(
            actor=ApiToken.generate(UserFactory())[0], related_to=dataset
        )

        migrations.get(MIGRATION).migrate(get_db())

        query = filter_by_actor_kinds(Activity.objects, ["HarvestSource", "ApiToken"])
        plan = query.order_by("-created_at").explain()["queryPlanner"]["winningPlan"]

        assert used_indexes(plan) == {"actor_kind_created_at"}
        assert {activity.id for activity in query} == {by_harvest.id, by_token.id}
