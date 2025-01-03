import pytest

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

    @pytest.mark.options(SEARCH_SERVICE_API_URL="https://example.com/")
    def test_search_query_to_search_service_url(self):
        class FakeAdapater:
            search_url = "search/"

        query = {
            "organization": "534fff81a3a7292c64a77e5c",
            "q": "insee",
            "sort": "-created",
            "page": 1,
            "page_size": 20,
            "tag": ["tag-1", "tag-2"],
        }
        search_query = SearchQuery(params=query)
        search_query.adapter = FakeAdapater()
        url = search_query.to_search_service_url()
        assert (
            url
            == "https://example.com/search/?q=insee&page=1&page_size=20&sort=-created&organization=534fff81a3a7292c64a77e5c&tag=tag-1&tag=tag-2"
        )
