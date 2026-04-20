import json
from udata.models import Dataset  # noqa
from ..models import VALIDATION_PENDING, HarvestSource
from ..csv import HarvestSourceCsvAdapter
from .factories import HarvestSourceFactory
from udata.tests.api import PytestOnlyDBTestCase


class HarvestSourceCSVAdapterTest(PytestOnlyDBTestCase):
    def test_harvest_source_csv_adapter(self):
        source = HarvestSourceFactory(validation={"state": VALIDATION_PENDING})
        config = {"extra_filters": [{"key": "test", "value": "test", "type": "test"}]}
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
        assert source_values["config"] == json.dumps(config)
