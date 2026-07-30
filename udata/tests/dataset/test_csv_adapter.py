import json
from datetime import datetime, timedelta

from udata.core.dataset.csv import DatasetCsvAdapter, ResourcesCsvAdapter
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.dataset.models import Dataset
from udata.core.spatial.factories import SAMPLE_GEOM, GeoLevelFactory, SpatialCoverageFactory
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.helpers import create_geozones_fixtures


class DatasetCSVAdapterTest(PytestOnlyDBTestCase):
    def test_resources_csv_adapter(self):
        date_created = datetime(2022, 12, 31)
        date_modified = date_created + timedelta(days=1)
        date_updated = date_created + timedelta(days=2)
        another_date = date_created + timedelta(days=42)
        dataset = DatasetFactory(
            resources=[
                ResourceFactory(
                    harvest={
                        "issued_at": date_created,
                        "modified_at": date_modified,
                        "last_update": date_updated,
                        "uri": "http://domain.gouv.fr/dataset/uri",
                    },
                    metrics={
                        "views": 42,
                    },
                )
            ],
            harvest={
                "domain": "example.com",
                "backend": "dummy_backend",
                "modified_at": another_date,
                "created_at": another_date,
                "last_update": another_date,
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
        # harvest.last_update
        assert date_updated.isoformat() in d_row
        # dataset harvest dates should not be here
        assert another_date.isoformat() not in d_row
        # assert resource metrics downloads
        assert 42 in d_row

    def test_datasets_csv_adapter(self):
        date_created = datetime(2022, 12, 31)
        date_issued = date_created + timedelta(days=1)
        date_modified = date_created + timedelta(days=2)
        date_updated = date_created + timedelta(days=3)
        harvest_dataset = DatasetFactory(
            harvest={
                "backend": "dummy_backend",
                "domain": "example.com",
                "remote_id": "remote-id",
                "remote_url": "https://www.example.com/",
                "uri": "https://www.example.com/remote-id",
                "created_at": date_created,
                "issued_at": date_issued,
                "modified_at": date_modified,
                "last_update": date_updated,
                "dct_identifier": "dct-identifier",
            },
        )
        resources_dataset = DatasetFactory(
            resources=[
                ResourceFactory(
                    metrics={
                        "views": 42,
                    },
                    format="csv",
                    type="main",
                ),
                ResourceFactory(
                    metrics={
                        "views": 1337,
                    },
                    format="json",
                ),
                ResourceFactory(),
            ]
        )
        paca, _, _ = create_geozones_fixtures()
        country = GeoLevelFactory(id="country", name="Pays", admin_level=10)
        spatial_zones_dataset = DatasetFactory(
            spatial=SpatialCoverageFactory(zones=[paca.id], granularity=country.id)
        )
        spatial_geom_dataset = DatasetFactory(spatial={"geom": SAMPLE_GEOM})
        adapter = DatasetCsvAdapter(Dataset.objects.all())

        # Build a dict (Dataset ID to dict of header name to value) from the CSV values and headers to simplify testing below.
        csv = {}
        for row in adapter.rows():
            values = dict(zip(adapter.header(), row))
            csv[values["id"]] = values

        harvest_dataset_values = csv[str(harvest_dataset.id)]
        assert harvest_dataset_values["harvest.backend"] == "dummy_backend"
        assert harvest_dataset_values["harvest.domain"] == "example.com"
        assert harvest_dataset_values["harvest.remote_id"] == "remote-id"
        assert harvest_dataset_values["harvest.remote_url"] == "https://www.example.com/"
        assert harvest_dataset_values["harvest.uri"] == "https://www.example.com/remote-id"
        assert harvest_dataset_values["harvest.created_at"] == date_created.isoformat()
        assert harvest_dataset_values["harvest.issued_at"] == date_issued.isoformat()
        assert harvest_dataset_values["harvest.modified_at"] == date_modified.isoformat()
        assert harvest_dataset_values["harvest.last_update"] == date_updated.isoformat()
        assert harvest_dataset_values["harvest.dct_identifier"] == "dct-identifier"
        assert harvest_dataset_values["resources_count"] == 0

        resources_dataset_values = csv[str(resources_dataset.id)]
        assert resources_dataset_values["resources_count"] == 3
        assert resources_dataset_values["main_resources_count"] == 1
        assert set(resources_dataset_values["resources_formats"].split(",")) == set(["csv", "json"])

        spatial_zones_dataset_values = csv[str(spatial_zones_dataset.id)]
        assert spatial_zones_dataset_values["spatial.zones"] == "Provence Alpes Côtes dAzur"
        assert spatial_zones_dataset_values["spatial.granularity"] == "country"

        spatial_geom_dataset_values = csv[str(spatial_geom_dataset.id)]
        assert json.loads(spatial_geom_dataset_values["spatial.geom"])["type"] == "MultiPolygon"
