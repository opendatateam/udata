from datetime import datetime, timedelta

from udata.core.dataservices.csv import DataserviceCsvAdapter
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.tests.api import PytestOnlyDBTestCase


class DataserviceCSVAdapterTest(PytestOnlyDBTestCase):
    def test_dataservices_csv_adapter(self):
        date_created = datetime(2022, 12, 31)
        date_issued = date_created + timedelta(days=1)
        date_modified = date_created + timedelta(days=2)
        date_updated = date_created + timedelta(days=3)
        dataservice = DataserviceFactory(
            created_at=date_created,
            metadata_modified_at=date_modified,
            organization=OrganizationFactory(),
            datasets=[DatasetFactory(), DatasetFactory()],
            metrics={"views": 42},
        )
        harvest_dataservice = DataserviceFactory(
            created_at=date_created,
            metadata_modified_at=date_modified,
            organization=OrganizationFactory(),
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
            },
        )
        [DataserviceFactory() for _ in range(10)]
        adapter = DataserviceCsvAdapter(Dataservice.objects.all())

        # Build a dict (Dataservice ID to dict of header name to value) from the CSV values and headers to simplify testing below.
        csv = {}
        for row in adapter.rows():
            values = dict(zip(adapter.header(), row))
            csv[values["id"]] = values

        dataservice_values = csv[str(dataservice.id)]
        assert dataservice_values["title"] == dataservice.title
        assert dataservice_values["url"] == dataservice.self_web_url()
        assert dataservice_values["organization"] == dataservice.organization.name
        assert dataservice_values["organization_id"] == str(dataservice.organization.id)
        assert dataservice_values["created_at"] == date_created.isoformat()
        assert dataservice_values["metadata_modified_at"] == date_modified.isoformat()
        assert dataservice_values["datasets"] == ",".join(
            str(dataset.id) for dataset in dataservice.datasets
        )
        assert dataservice_values["metric.views"] == dataservice.metrics["views"]

        harvest_dataservice_values = csv[str(harvest_dataservice.id)]
        assert harvest_dataservice_values["harvest.backend"] == "dummy_backend"
        assert harvest_dataservice_values["harvest.domain"] == "example.com"
        assert harvest_dataservice_values["harvest.remote_id"] == "remote-id"
        assert harvest_dataservice_values["harvest.remote_url"] == "https://www.example.com/"
        assert harvest_dataservice_values["harvest.uri"] == "https://www.example.com/remote-id"
        assert harvest_dataservice_values["harvest.created_at"] == date_created.isoformat()
        assert harvest_dataservice_values["harvest.issued_at"] == date_issued.isoformat()
        assert harvest_dataservice_values["harvest.modified_at"] == date_modified.isoformat()
        assert harvest_dataservice_values["harvest.last_update"] == date_updated.isoformat()
