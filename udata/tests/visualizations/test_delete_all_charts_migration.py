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
