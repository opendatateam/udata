from udata.search.query import (
    DEFAULT_MAX_FACET_SIZE,
    DEFAULT_PAGE_SIZE,
    SearchQuery,
    parse_facet_size,
)
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

    def test_search_query_to_search_params(self):
        query = {
            "organization": "534fff81a3a7292c64a77e5c",
            "q": "insee",
            "sort": "-created",
            "page": 1,
            "page_size": 20,
            "tag": ["tag-1", "tag-2"],
        }
        search_query = SearchQuery(params=query)
        params = search_query.to_search_params()
        assert params["q"] == "insee"
        assert params["page"] == 1
        assert params["page_size"] == 20
        assert params["sort"] == "-created"
        assert params["organization"] == "534fff81a3a7292c64a77e5c"
        assert params["tag"] == ["tag-1", "tag-2"]

    def test_facet_sizes_default_empty(self):
        search_query = SearchQuery(params={})
        assert search_query._facet_sizes == {}

    def test_facet_size_param_parsed(self):
        query = {"facet_size__organization_id_with_name": "200"}
        search_query = SearchQuery(params=query)
        assert search_query._facet_sizes == {"organization_id_with_name": 200}

    def test_multiple_facet_size_params_parsed(self):
        query = {"facet_size__organization_id_with_name": "200", "facet_size__tag": "100"}
        search_query = SearchQuery(params=query)
        assert search_query._facet_sizes == {"organization_id_with_name": 200, "tag": 100}

    def test_facet_size_params_not_in_filters(self):
        query = {"facet_size__organization_id_with_name": "200", "tag": "transport"}
        search_query = SearchQuery(params=query)
        assert "facet_size__organization_id_with_name" not in search_query._filters
        assert search_query._filters == {"tag": "transport"}

    def test_facet_sizes_included_in_search_params(self):
        query = {"facet_size__organization_id_with_name": "200", "q": "test"}
        search_query = SearchQuery(params=query)
        params = search_query.to_search_params()
        assert params["facet_sizes"] == {"organization_id_with_name": 200}

    def test_facet_size_zero_raises_400(self):
        with self.assertRaises(Exception) as ctx:
            SearchQuery(params={"facet_size__tag": "0"})
        assert ctx.exception.code == 400

    def test_facet_size_negative_raises_400(self):
        with self.assertRaises(Exception) as ctx:
            SearchQuery(params={"facet_size__tag": "-1"})
        assert ctx.exception.code == 400

    def test_facet_size_non_integer_raises_400(self):
        with self.assertRaises(Exception) as ctx:
            SearchQuery(params={"facet_size__tag": "big"})
        assert ctx.exception.code == 400

    def test_facet_size_exceeds_max_raises_400(self):
        with self.assertRaises(Exception) as ctx:
            SearchQuery(params={"facet_size__tag": str(DEFAULT_MAX_FACET_SIZE + 1)})
        assert ctx.exception.code == 400

    def test_facet_size_at_max_is_valid(self):
        search_query = SearchQuery(params={"facet_size__tag": str(DEFAULT_MAX_FACET_SIZE)})
        assert search_query._facet_sizes["tag"] == DEFAULT_MAX_FACET_SIZE


class ParseFacetSizeTest(APITestCase):
    def test_valid_integer(self):
        assert parse_facet_size("facet_size__tag", "50", 500) == 50

    def test_non_integer_raises_400(self):
        with self.assertRaises(Exception) as ctx:
            parse_facet_size("facet_size__tag", "abc", 500)
        assert ctx.exception.code == 400

    def test_zero_raises_400(self):
        with self.assertRaises(Exception) as ctx:
            parse_facet_size("facet_size__tag", "0", 500)
        assert ctx.exception.code == 400

    def test_negative_raises_400(self):
        with self.assertRaises(Exception) as ctx:
            parse_facet_size("facet_size__tag", "-5", 500)
        assert ctx.exception.code == 400

    def test_exceeds_max_raises_400(self):
        with self.assertRaises(Exception) as ctx:
            parse_facet_size("facet_size__tag", "501", 500)
        assert ctx.exception.code == 400

    def test_at_max_is_valid(self):
        assert parse_facet_size("facet_size__tag", "500", 500) == 500

    def test_at_min_is_valid(self):
        assert parse_facet_size("facet_size__tag", "1", 500) == 1
