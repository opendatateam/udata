from datetime import datetime

import pytest

from udata.core.dataservices.csv import DataserviceCsvAdapter
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory


@pytest.mark.frontend
@pytest.mark.usefixtures("clean_db")
class DataserviceCSVAdapterTest:
    def test_dataservices_csv_adapter(self):
        dataservice = DataserviceFactory(
            created_at=datetime(2022, 12, 31),
            metadata_modified_at=datetime(2023, 1, 1),
            organization=OrganizationFactory(),
            datasets=[DatasetFactory(), DatasetFactory()],
            metrics={"views": 42},
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
        assert dataservice_values["created_at"] == dataservice.created_at.isoformat()
        assert (
            dataservice_values["metadata_modified_at"]
            == dataservice.metadata_modified_at.isoformat()
        )
        assert dataservice_values["datasets"] == ",".join(
            str(dataset.id) for dataset in dataservice.datasets
        )
        assert dataservice_values["metric.views"] == dataservice.metrics["views"]
