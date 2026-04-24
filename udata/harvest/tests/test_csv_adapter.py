import json
from datetime import datetime

from bson import ObjectId

from udata.tests.api import PytestOnlyDBTestCase

from ..csv import HarvestSourceCsvAdapter
from ..models import VALIDATION_PENDING, HarvestSource
from .factories import HarvestSourceFactory


class HarvestSourceCSVAdapterTest(PytestOnlyDBTestCase):
    def test_harvest_source_csv_adapter(self):
        source = HarvestSourceFactory(validation={"state": VALIDATION_PENDING})
        config = {
            "filters": [
                {"key": "date", "type": "include", "value": datetime(year=2026, month=4, day=24)},
                {
                    "key": "organization",
                    "type": "include",
                    "value": ObjectId("646b7187b50b2a93b1ae3d45"),
                },
            ],
            "extra_filters": [{"key": "test", "value": "test", "type": "test"}],
        }
        source_with_config = HarvestSourceFactory(config=config)

        adapter = HarvestSourceCsvAdapter(HarvestSource.objects.all())

        # Build a dict (Source ID to dict of header name to value) from the CSV values and headers to simplify testing below.
        csv = {}
        for row in adapter.rows():
            values = dict(zip(adapter.header(), row))
            csv[values["id"]] = values

        source_values = csv[str(source.id)]
        assert source_values["config"] == "{}"
        assert source_values["validation"] == "pending"

        source_values = csv[str(source_with_config.id)]
        assert source_values["config"] == json.dumps(config, default=str)
