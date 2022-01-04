import pytest

from werkzeug.urls import url_decode, url_parse

from udata import search
from udata.tests.helpers import assert_json_equal
from udata.utils import multi_to_dict

from . import FakeSearchable, FakeFactory, FakeSearch


class FuzzySearch(FakeSearch):
    fuzzy = True


#############################################################################
#                     Elasticsearch DSL specific helpers                    #
#############################################################################

def get_body(facet_search):
    '''Extract the JSON body from a FacetedSearch'''
    return facet_search._s.to_dict()


def get_query(facet_search):
    '''Extract the query part from a FacetedSearch'''
    return get_body(facet_search).get('query')


#############################################################################
#                                  Tests                                    #
#############################################################################

class SearchQueryTest:
    def test_execute_search_result(self, rmock):
        '''Should return a SearchResult with the right model'''
        rmock.get('mock://test.com/fakeable/?q=&page=1&page_size=20', text=[])
        result = search.query(FakeSearch)
        assert isinstance(result, search.SearchResult)
        assert result.query.adapter == FakeSearch

    def test_execute_search_result_with_model(self):
        '''Should return a SearchResult with the right model'''
        result = search.query(FakeSearchable)
        assert isinstance(result, search.SearchResult)
        assert result.query.adapter == FakeSearch

    def test_should_not_fail_on_missing_objects(self):
        FakeFactory.create_batch(3)
        deleted_fake = FakeFactory()

        result = search.query(FakeSearch)
        deleted_fake.delete()
        assert len(result) == 4

        # Missing object should be filtered out
        objects = result.objects
        assert len(objects) == 3
        for o in objects:
            assert isinstance(o, FakeSearchable)

    def test_only_id(self):
        '''Should only fetch id field'''
        search_query = search.search_for(FakeSearch)
        body = get_body(search_query)
        assert body['fields'] == []

    def test_empty_search(self):
        '''An empty query should match all documents'''
        search_query = search.search_for(FakeSearch)
        body = get_body(search_query)
        assert body['query'] == {'match_all': {}}
        assert 'aggregations' not in body
        assert 'aggs' not in body
        assert 'sort' not in body

    def test_paginated_search(self):
        '''Search should handle pagination'''
        search_query = search.search_for(FakeSearch, page=3, page_size=10)
        body = get_body(search_query)
        assert 'from' in body
        assert body['from'] == 20
        assert 'size' in body
        assert body['size'] == 10

    def test_sorted_search_asc(self):
        '''Search should sort by field in ascending order'''
        search_query = search.search_for(FakeSearch, sort='title')
        body = get_body(search_query)
        assert body['sort'] == [{'title.raw': 'asc'}]

    def test_sorted_search_desc(self):
        '''Search should sort by field in descending order'''
        search_query = search.search_for(FakeSearch, sort='-title')
        body = get_body(search_query)
        assert body['sort'] == [{'title.raw': 'desc'}]

    def test_multi_sorted_search(self):
        '''Search should sort'''
        search_query = search.search_for(FakeSearch,
                                         sort=['-title', 'description'])
        body = get_body(search_query)
        assert body['sort'] == [
            {'title.raw': 'desc'},
            {'description.raw': 'asc'},
        ]

    def test_ignore_unkown_parameters(self):
        '''Should ignore unknown parameters'''
        # Should not raise any exception
        search.search_for(FakeSearch, unknown='whatever')

    def test_to_url(self, app):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
            'facets': True,
        }
        search_query = search.search_for(FakeSearch, **kwargs)
        with app.test_request_context('/an_url'):
            url = search_query.to_url()
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        assert parsed_url.path == '/an_url'
        assert_json_equal(multi_to_dict(qs), {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': '2',
        })

    def test_to_url_with_override(self, app):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
        }
        search_query = search.search_for(FakeSearch, **kwargs)
        with app.test_request_context('/an_url'):
            url = search_query.to_url(tag='tag3', other='value')
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        assert parsed_url.path == '/an_url'
        assert_json_equal(multi_to_dict(qs), {
            'q': 'test',
            'tag': ['tag1', 'tag2', 'tag3'],
            'other': 'value',
        })

    def test_to_url_with_override_and_replace(self, app):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
        }
        search_query = search.search_for(FakeSearch, **kwargs)
        with app.test_request_context('/an_url'):
            url = search_query.to_url(tag='tag3', other='value', replace=True)
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        assert parsed_url.path == '/an_url'
        assert_json_equal(multi_to_dict(qs), {
            'q': 'test',
            'tag': 'tag3',
            'other': 'value',
        })

    def test_to_url_with_none(self, app):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
        }
        search_query = search.search_for(FakeSearch, **kwargs)
        with app.test_request_context('/an_url'):
            url = search_query.to_url(tag=None, other='value', replace=True)
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        assert parsed_url.path == '/an_url'
        assert_json_equal(multi_to_dict(qs), {
            'q': 'test',
            'other': 'value',
        })

    def test_to_url_with_specified_url(self, app):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
        }
        search_query = search.search_for(FakeSearch, **kwargs)
        with app.test_request_context('/an_url'):
            url = search_query.to_url('/another_url')
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        assert parsed_url.path == '/another_url'
        assert_json_equal(multi_to_dict(qs), {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': '2',
        })
