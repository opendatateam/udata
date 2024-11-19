from unittest.mock import patch

from flask import current_app

from udata.core.dataset.search import DatasetSearch
from udata.search.query import DEFAULT_PAGE_SIZE, SearchQuery
from udata.tests.api import APITestCase


class QueryTest(APITestCase):
    def test_search_query_with_params(self):
        query = {
            "organization": "534fff81a3a7292c64a77e5c",
            "q": "insee",
            "sort": "-created",
            "page": 1,
            "page_size": 20,
        }
        search_query = SearchQuery(params=query)
        assert search_query.page == 1
        assert search_query.page_size == 20
        assert search_query._query == "insee"
        assert search_query.sort == "-created"
        assert search_query._filters["organization"] == "534fff81a3a7292c64a77e5c"

    def test_search_query_without_params(self):
        search_query = SearchQuery(params={})
        assert search_query.page == 1
        assert search_query.page_size == DEFAULT_PAGE_SIZE
        assert search_query._query == ""
        assert search_query.sort is None
        assert search_query._filters == {}

    def test_search_query_to_url(self):
        query = {
            "organization": "534fff81a3a7292c64a77e5c",
            "q": "insee",
            "sort": "-created",
            "page": 1,
            "page_size": 20,
        }
        search_query = SearchQuery(params=query)
        url = search_query.to_url()
        assert "organization=534fff81a3a7292c64a77e5c&q=insee&sort=-created&page=1" in url

    @patch("requests.get")
    # Mock udata.search.result.SearchResult, used in SearchQuery.execute_search.
    @patch("udata.search.query.SearchResult")
    def test_search_query_for_search_service(self, search_result_req, mock_req):
        """When using the search service, boolean filters need to be converted to 0 or 1."""
        current_app.config["SEARCH_SERVICE_API_URL"] = "http://example.com/"
        query = {
            "featured": "true",
            "page": 1,
            "page_size": 20,
        }
        search_query = SearchQuery(query)
        search_query.adapter = DatasetSearch
        search_query.execute_search()
        mock_req.assert_called_with(
            "http://example.com/datasets/?q=&page=1&page_size=20&featured=1", timeout=20
        )

        query["featured"] = "false"
        search_query = SearchQuery(query)
        search_query.adapter = DatasetSearch
        search_query.execute_search()
        mock_req.assert_called_with(
            "http://example.com/datasets/?q=&page=1&page_size=20&featured=0", timeout=20
        )
