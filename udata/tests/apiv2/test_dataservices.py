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

    def test_dataservice_search_single_tag(self):
        tag_dataservice = DataserviceFactory(tags=["my-tag", "other"])
        DataserviceFactory(tags=["unrelated"])

        response = self.get("/api/2/dataservices/search/?tag=my-tag")
        self.assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(tag_dataservice.id)

    def test_dataservice_search_multiple_tags(self):
        tag_dataservice = DataserviceFactory(tags=["my-tag", "other"])
        DataserviceFactory(tags=["my-tag"])

        response = self.get("/api/2/dataservices/search/?tag=my-tag&tag=other")
        self.assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(tag_dataservice.id)
