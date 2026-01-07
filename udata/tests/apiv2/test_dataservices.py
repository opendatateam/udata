from udata.core.dataservices.factories import DataserviceFactory
from udata.tests.api import APITestCase


class DataserviceSearchAPIV2Test(APITestCase):
    def test_dataservice_search_with_model_query_param(self):
        """Searching dataservices with 'model' as query param should not crash.

        Regression test for: TypeError: query() got multiple values for argument 'model'
        """
        DataserviceFactory.create_batch(3)

        response = self.get("/api/2/dataservices/search/?model=malicious")
        self.assert200(response)
