from mongoengine.connection import get_db

from udata.core.visualizations.factories import ChartFactory, FilterFactory
from udata.core.visualizations.models import AndFilters, Chart
from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase

MIGRATION = "2026-09-11-backfill-filter-cls.py"


def migrate():
    migrations.get(MIGRATION).migrate(get_db())


def strip_cls(chart, *indexes):
    """Rewrite a chart's stored filter group elements without their `_cls`,
    as they were before nested filter groups existed."""
    group = {"_cls": "AndFilters", "filters": []}
    for i in indexes:
        group["filters"].append({"column": f"col{i}", "condition": "exact", "value": str(i)})
    Chart._get_collection().update_one({"_id": chart.id}, {"$set": {"series.0.filters": group}})


class BackfillFilterClsMigrationTest(PytestOnlyDBTestCase):
    def test_elements_without_cls_get_filter_cls(self):
        chart = ChartFactory()

        strip_cls(chart, 1, 2)
        migrate()

        group = Chart._get_collection().find_one({"_id": chart.id})["series"][0]["filters"]
        assert [f["_cls"] for f in group["filters"]] == ["Filter", "Filter"]

    def test_elements_already_having_cls_are_left_alone(self):
        chart = ChartFactory(series__0__filters=AndFilters(filters=[FilterFactory()]))

        migrate()

        stored = Chart._get_collection().find_one({"_id": chart.id})["series"][0]["filters"]
        assert stored["filters"][0]["_cls"] == "Filter"

    def test_other_chart_fields_are_untouched(self):
        chart = ChartFactory()

        strip_cls(chart, 1)
        migrate()

        reloaded = Chart.objects.get(id=chart.id)
        assert reloaded.title == chart.title
        assert reloaded.series[0].filters.filters[0].column == "col1"
