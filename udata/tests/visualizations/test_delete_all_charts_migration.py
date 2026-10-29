from datetime import UTC, datetime

from mongoengine.connection import get_db

from udata.core.user.factories import UserFactory
from udata.core.visualizations.factories import ChartFactory
from udata.core.visualizations.models import Chart
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-10-22-delete-all-charts.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


class DeleteAllChartsMigrationTest(PytestOnlyDBTestCase):
    def test_delete_all_charts(self):
        """The migration should delete every chart"""
        ChartFactory.create_batch(3)
        migrate()
        assert Chart.objects.count() == 0

    def test_delete_all_charts_with_owner(self):
        """The migration should delete charts owned by users as well"""
        user = UserFactory()
        ChartFactory.create_batch(2, owner=user)
        migrate()
        assert Chart.objects.count() == 0

    def test_delete_all_charts_with_legacy_shaped_documents(self):
        """Legacy-shaped documents (fields the current model no longer has, or
        fields missing) must be deletable without unmarshalling them."""
        collection = get_db()["chart"]
        ChartFactory()
        legacy_id = collection.insert_one(
            {
                "title": "Legacy chart",
                "slug": "legacy-chart",
                "query": "SELECT 1",
                # Legacy shape: an old free-form ``config`` dict, no chart_type,
                # no y_axis, and an image field that predates the thumbnails map.
                "config": {"x": "a", "y": "b", "kind": "line"},
                "image": {"filename": "ab/cd/legacy.png", "original": "ab/cd/legacy_o.png"},
                "created_at": datetime.now(UTC),
            }
        ).inserted_id

        migrate()

        assert collection.count_documents({}) == 0
        assert collection.find_one({"_id": legacy_id}) is None
