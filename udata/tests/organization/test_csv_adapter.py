import pytest

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.organization.csv import OrganizationCsvAdapter
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Organization


@pytest.mark.frontend
@pytest.mark.usefixtures("clean_db")
class OrganizationCSVAdapterTest:
    def test_organization_downloads_counts(self):
        org_with_dataset = OrganizationFactory()
        org_without_dataset = OrganizationFactory()

        DatasetFactory(
            organization=org_with_dataset,
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
            ],
        )
        DatasetFactory(organization=org_with_dataset, resources=[])
        adapter = OrganizationCsvAdapter(Organization.objects.all())

        # Build a dict (Org ID to dict of header name to value) from the CSV values and headers to simplify testing below.
        csv = {}
        for row in adapter.rows():
            values = dict(zip(adapter.header(), row))
            csv[values["id"]] = values

        org_values = csv[str(org_with_dataset.id)]
        assert org_values["downloads"] == 1337 + 42

        org_values = csv[str(org_without_dataset.id)]
        assert org_values["downloads"] == 0
