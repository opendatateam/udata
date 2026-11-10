from mongoengine.connection import get_db

from udata.core.activity.models import Activity, filter_by_actor_kinds
from udata.db import migrations
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
        migrations.get(MIGRATION).migrate(get_db())

        query = filter_by_actor_kinds(Activity.objects, ["HarvestSource", "ApiToken"])
        plan = query.order_by("-created_at").explain()["queryPlanner"]["winningPlan"]

        assert used_indexes(plan) == {"actor_kind_created_at"}

    def test_it_can_run_again(self):
        migrations.get(MIGRATION).migrate(get_db())
        migrations.get(MIGRATION).migrate(get_db())

        assert "actor_kind_created_at" in get_db().activity.index_information()
