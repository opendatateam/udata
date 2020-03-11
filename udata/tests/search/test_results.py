import pytest

from udata import search

from . import response_factory, FakeSearch


@pytest.mark.usefixtures('app')
class SearchResultTest:
    def factory(self, response=None, **kwargs):
        '''
        Build a fake SearchResult.
        '''
        response = response or response_factory()
        query = search.search_for(FakeSearch, **kwargs)
        return search.SearchResult(query, response)

    def test_properties(self):
        '''Search result should map some properties for easy access'''
        response = response_factory(nb=10, total=42)
        max_score = response['hits']['max_score']
        result = self.factory(response)

        assert result.total == 42
        assert result.max_score == max_score

        ids = result.get_ids()
        assert len(ids) == 10

    def test_no_failures(self):
        '''Search result should not fail on missing properties'''
        response = response_factory()
        del response['hits']['total']
        del response['hits']['max_score']
        del response['hits']['hits']
        result = self.factory(response)

        assert result.total == 0
        assert result.max_score == 0

        ids = result.get_ids()
        assert len(ids) == 0

    def test_pagination(self):
        '''Search results should be paginated'''
        response = response_factory(nb=3, total=11)
        result = self.factory(response, page=2, page_size=3)

        assert result.page == 2
        assert result.page_size == 3
        assert result.pages == 4

    def test_pagination_empty(self):
        '''Search results should be paginated even if empty'''
        response = response_factory()
        del response['hits']['total']
        del response['hits']['max_score']
        del response['hits']['hits']
        result = self.factory(response, page=2, page_size=3)

        assert result.page == 1
        assert result.page_size == 3
        assert result.pages == 0

    def test_no_pagination_in_query(self):
        '''Search results should be paginated even if not asked'''
        response = response_factory(nb=1, total=1)
        result = self.factory(response)

        assert result.page == 1
        assert result.page_size == search.DEFAULT_PAGE_SIZE
        assert result.pages == 1
