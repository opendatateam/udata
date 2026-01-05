from udata.core.dataservices.factories import DataserviceFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.tests.api import APITestCase


class SearchAPIV2Test(APITestCase):
    def test_dataservice_search_with_model_query_param(self):
        """Searching dataservices with 'model' as query param should not crash.

        Regression test for: TypeError: query() got multiple values for argument 'model'
        """
        DataserviceFactory.create_batch(3)

        response = self.get("/api/2/dataservices/search/?model=malicious")
        self.assert200(response)

    def test_reuse_search_with_model_query_param(self):
        """Searching reuses with 'model' as query param should not crash."""
        ReuseFactory.create_batch(3)

        response = self.get("/api/2/reuses/search/?model=malicious")
        self.assert200(response)

    def test_organization_search_with_model_query_param(self):
        """Searching organizations with 'model' as query param should not crash."""
        OrganizationFactory.create_batch(3)

        response = self.get("/api/2/organizations/search/?model=malicious")
        self.assert200(response)
