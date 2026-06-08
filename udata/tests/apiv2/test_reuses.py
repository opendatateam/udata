from udata.core.reuse.factories import ReuseFactory
from udata.search.query import ES_MAX_RESULT_WINDOW
from udata.tests.api import APITestCase


class ReuseSearchAPIV2Test(APITestCase):
    def test_reuse_search_with_model_query_param(self):
        """Searching reuses with 'model' as query param should not crash."""
        ReuseFactory.create_batch(3)

        response = self.get("/api/2/reuses/search/?model=malicious")
        self.assert200(response)

    def test_search_returns_400_when_pagination_exceeds_es_max_result_window(self):
        response = self.get("/api/2/reuses/search/?page=8925&page_size=20")
        self.assert400(response)
        max_page = ES_MAX_RESULT_WINDOW // 20
        assert f"Maximum page for this page_size is {max_page}" in response.json["message"]
