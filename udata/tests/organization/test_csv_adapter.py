from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.csv import OrganizationCsvAdapter
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Organization
from udata.tests.api import PytestOnlyDBTestCase


class OrganizationCSVAdapterTest(PytestOnlyDBTestCase):
    def test_organization_downloads_counts(self):
        org_with_dataset = OrganizationFactory()
        org_without_dataset = OrganizationFactory()

        DatasetFactory(
            organization=org_with_dataset,
            metrics={"resources_downloads": 1337},
        )
        DatasetFactory(organization=org_with_dataset, metrics={"resources_downloads": 42})
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
