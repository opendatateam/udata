from udata.core.reuse.factories import VisibleReuseFactory
from udata.tests.api import APITestCase


class ReuseSearchAPIV2Test(APITestCase):
    def test_reuse_search_with_model_query_param(self):
        """Searching reuses with 'model' as query param should not crash."""
        VisibleReuseFactory.create_batch(3)

        response = self.get("/api/2/reuses/search/?model=malicious")
        self.assert200(response)

    def test_reuse_search_single_tag(self):
        tag_reuse = VisibleReuseFactory(tags=["my-tag", "other"])
        VisibleReuseFactory(tags=["unrelated"])

        response = self.get("/api/2/reuses/search/?tag=my-tag")
        self.assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(tag_reuse.id)

    def test_reuse_search_multiple_tags(self):
        tag_reuse = VisibleReuseFactory(tags=["my-tag", "other"])
        VisibleReuseFactory(tags=["my-tag"])

        response = self.get("/api/2/reuses/search/?tag=my-tag&tag=other")
        self.assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(tag_reuse.id)
