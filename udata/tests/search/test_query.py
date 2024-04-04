from udata.tests.api import APITestCase
from udata.search.query import SearchQuery, DEFAULT_PAGE_SIZE


class QueryTest(APITestCase):
    def test_search_query_with_params(self):
        query = {
            'organization': '534fff81a3a7292c64a77e5c',
            'q': 'insee',
            'sort': '-created',
            'page': 1,
            'page_size': 20
        }
        search_query = SearchQuery(params=query)
        assert search_query.page == 1
        assert search_query.page_size == 20
        assert search_query._query == 'insee'
        assert search_query.sort == '-created'
        assert search_query._filters['organization'] == '534fff81a3a7292c64a77e5c'

    def test_search_query_without_params(self):
        search_query = SearchQuery(params={})
        assert search_query.page == 1
        assert search_query.page_size == DEFAULT_PAGE_SIZE
        assert search_query._query == ''
        assert search_query.sort is None
        assert search_query._filters == {}

    def test_search_query_to_url(self):
        query = {
            'organization': '534fff81a3a7292c64a77e5c',
            'q': 'insee',
            'sort': '-created',
            'page': 1,
            'page_size': 20
        }
        search_query = SearchQuery(params=query)
        url = search_query.to_url()
        assert 'organization=534fff81a3a7292c64a77e5c&q=insee&sort=-created&page=1' in url
