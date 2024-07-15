from datetime import datetime, timedelta

import pytest

from udata.core.dataset.csv import DatasetCsvAdapter, ResourcesCsvAdapter
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.dataset.models import Dataset


@pytest.mark.frontend
@pytest.mark.usefixtures("clean_db")
class DatasetCSVAdapterTest:
    def test_resources_csv_adapter(self):
        date_created = datetime(2022, 12, 31)
        date_modified = date_created + timedelta(days=1)
        another_date = date_created + timedelta(days=42)
        dataset = DatasetFactory(
            resources=[
                ResourceFactory(
                    harvest={
                        "created_at": date_created,
                        "modified_at": date_modified,
                        "uri": "http://domain.gouv.fr/dataset/uri",
                    }
                )
            ],
            harvest={
                "domain": "example.com",
                "backend": "dummy_backend",
                "modified_at": another_date,
                "created_at": another_date,
            },
        )
        DatasetFactory(resources=[ResourceFactory()])
        adapter = ResourcesCsvAdapter(Dataset.objects.all())
        rows = list(adapter.rows())
        d_row = [r for r in rows if str(dataset.id) in r][0]
        # harvest.created_at
        assert date_created.isoformat() in d_row
        # harvest.modified_at
        assert date_modified.isoformat() in d_row
        # dataset harvest dates should not be here
        assert another_date.isoformat() not in d_row

    def test_datasets_csv_adapter(self):
        date_created = datetime(2022, 12, 31)
        date_modified = date_created + timedelta(days=1)
        harvest_dataset = DatasetFactory(
            harvest={
                "domain": "example.com",
                "backend": "dummy_backend",
                "modified_at": date_modified,
                "created_at": date_created,
            },
        )
        resources_dataset = DatasetFactory(
            resources=[
                ResourceFactory(
                    metrics={
                        "views": 42,
                    }
                ),
                ResourceFactory(
                    metrics={
                        "views": 1337,
                    }
                ),
                ResourceFactory(),
            ]
        )
        adapter = DatasetCsvAdapter(Dataset.objects.all())

        # Build a dict (Dataset ID to dict of header name to value) from the CSV values and headers to simplify testing below.
        csv = {}
        for row in adapter.rows():
            values = dict(zip(adapter.header(), row))
            csv[values["id"]] = values

        harvest_dataset_values = csv[str(harvest_dataset.id)]
        assert harvest_dataset_values["harvest.created_at"] == date_created.isoformat()
        assert harvest_dataset_values["harvest.modified_at"] == date_modified.isoformat()
        assert harvest_dataset_values["harvest.backend"] == "dummy_backend"
        assert harvest_dataset_values["harvest.domain"] == "example.com"
        assert harvest_dataset_values["resources_count"] == 0
        assert harvest_dataset_values["downloads"] == 0

        resources_dataset_values = csv[str(resources_dataset.id)]
        assert resources_dataset_values["resources_count"] == 3
        assert resources_dataset_values["downloads"] == 1337 + 42
