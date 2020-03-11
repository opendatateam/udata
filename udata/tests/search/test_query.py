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

@pytest.mark.usefixtures('autoindex')
class SearchQueryTest:
    def test_execute_search_result(self):
        '''Should return a SearchResult with the right model'''
        result = search.query(FakeSearch)
        assert isinstance(result, search.SearchResult)
        assert result.query.adapter == FakeSearch

    def test_execute_search_result_with_model(self):
        '''Should return a SearchResult with the right model'''
        result = search.query(FakeSearchable)
        assert isinstance(result, search.SearchResult)
        assert result.query.adapter == FakeSearch

    def test_should_not_fail_on_missing_objects(self, autoindex):
        with autoindex:
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

    def test_custom_scoring(self):
        '''Search should handle field boosting'''
        class FakeBoostedSearch(FakeSearch):
            boosters = [
                search.BoolBooster('some_bool_field', 1.1)
            ]

        query = search.search_for(FakeBoostedSearch)
        body = get_body(query)
        # Query should be wrapped in function_score
        assert 'function_score' in body['query']
        assert 'query' in body['query']['function_score']
        assert 'functions' in body['query']['function_score']
        first_function = body['query']['function_score']['functions'][0]
        assert_json_equal(first_function, {
            'filter': {'term': {'some_bool_field': True}},
            'boost_factor': 1.1,
        })

    def test_value_factor_without_parameters(self):
        '''Search should handle field value factor without parameters'''
        class FakeValueFactorSearch(FakeSearch):
            boosters = [
                search.ValueFactor('some_int_field')
            ]

        query = search.search_for(FakeValueFactorSearch)
        body = get_body(query)
        # Query should be wrapped in function_score
        assert 'function_score' in body['query']
        assert 'query' in body['query']['function_score']
        assert 'functions' in body['query']['function_score']
        value_factor = body['query']['function_score']['functions'][0]
        # Should add be field_value_factor with parameter function
        assert_json_equal(value_factor, {
            'field_value_factor': {
                'field': 'some_int_field'
            }
        })

    def test_value_factor_with_parameters(self):
        '''Search should handle field value factor with parameters'''
        class FakeValueFactorSearch(FakeSearch):
            boosters = [
                search.ValueFactor('some_int_field',
                                   factor=1.2,
                                   modifier='sqrt',
                                   missing=1)
            ]

        query = search.search_for(FakeValueFactorSearch)
        body = get_body(query)
        # Query should be wrapped in function_score
        assert 'function_score' in body['query']
        assert 'query' in body['query']['function_score']
        assert 'functions' in body['query']['function_score']
        value_factor = body['query']['function_score']['functions'][0]
        # Should add be field_value_factor with parameter function
        assert_json_equal(value_factor, {
            'field_value_factor': {
                'field': 'some_int_field',
                'factor': 1.2,
                'modifier': 'sqrt',
                'missing': 1
            }
        })

    def test_decay_function_scoring(self):
        '''Search should handle field decay'''
        class FakeBoostedSearch(FakeSearch):
            boosters = [
                search.GaussDecay('a_num_field', 10),
                search.ExpDecay('another_field', 20),
                search.LinearDecay('last_field', 30),
            ]

        query = search.search_for(FakeBoostedSearch)
        body = get_body(query)
        functions = body['query']['function_score']['functions']
        # Query should be wrapped in a gaus decay function
        assert_json_equal(functions[0], {
            'gauss': {
                'a_num_field': {
                    'origin': 10,
                    'scale': 10,
                }
            },
        })
        assert_json_equal(functions[1], {
            'exp': {
                'another_field': {
                    'origin': 20,
                    'scale': 20,
                }
            },
        })
        assert_json_equal(functions[2], {
            'linear': {
                'last_field': {
                    'origin': 30,
                    'scale': 30,
                }
            },
        })

    def test_decay_function_scoring_with_options(self):
        '''Search should handle field decay with options'''
        class FakeBoostedSearch(FakeSearch):
            boosters = [
                search.GaussDecay('a_num_field', 10, 20, offset=5, decay=0.5),
                search.ExpDecay(
                    'another_field', 20, scale=30, offset=5, decay=0.5),
                search.LinearDecay('last_field', 30, 40, offset=5, decay=0.5),
            ]

        query = search.search_for(FakeBoostedSearch)
        body = get_body(query)
        functions = body['query']['function_score']['functions']
        # Query should be wrapped in a gaus decay function
        assert_json_equal(functions[0], {
            'gauss': {
                'a_num_field': {
                    'origin': 10,
                    'scale': 20,
                    'offset': 5,
                    'decay': 0.5,
                }
            },
        })
        assert_json_equal(functions[1], {
            'exp': {
                'another_field': {
                    'origin': 20,
                    'scale': 30,
                    'offset': 5,
                    'decay': 0.5,
                }
            },
        })
        assert_json_equal(functions[2], {
            'linear': {
                'last_field': {
                    'origin': 30,
                    'scale': 40,
                    'offset': 5,
                    'decay': 0.5
                }
            },
        })

    def test_decay_function_scoring_with_callables(self):
        '''Search should handle field decay with options'''
        get_dot5 = lambda: 0.5  # noqa
        get_5 = lambda: 5  # noqa
        get_10 = lambda: 10  # noqa
        get_20 = lambda: 20  # noqa
        get_30 = lambda: 30  # noqa
        get_40 = lambda: 40  # noqa

        class FakeBoostedSearch(FakeSearch):
            boosters = [
                search.GaussDecay('a_num_field', get_10,
                                  get_20, offset=get_5, decay=get_dot5),
                search.ExpDecay('another_field', get_20,
                                scale=get_30, offset=get_5, decay=get_dot5),
                search.LinearDecay('last_field', get_30,
                                   get_40, offset=get_5, decay=get_dot5),
            ]

        query = search.search_for(FakeBoostedSearch)
        body = get_body(query)
        functions = body['query']['function_score']['functions']
        # Query should be wrapped in a gaus decay function
        assert_json_equal(functions[0], {
            'gauss': {
                'a_num_field': {
                    'origin': 10,
                    'scale': 20,
                    'offset': 5,
                    'decay': 0.5,
                }
            },
        })
        assert functions[1] == {
            'exp': {
                'another_field': {
                    'origin': 20,
                    'scale': 30,
                    'offset': 5,
                    'decay': 0.5,
                }
            },
        }
        assert functions[2] == {
            'linear': {
                'last_field': {
                    'origin': 30,
                    'scale': 40,
                    'offset': 5,
                    'decay': 0.5
                }
            },
        }

    def test_custom_function_scoring(self):
        '''Search should handle field boosting by function'''
        class FakeBoostedSearch(FakeSearch):
            boosters = [
                search.FunctionBooster('doc["field"].value * 2')
            ]

        query = search.search_for(FakeBoostedSearch)
        body = get_body(query)
        # Query should be wrapped in function_score
        score_function = body['query']['function_score']['functions'][0]
        assert_json_equal(score_function, {
            'script_score': {'script': 'doc["field"].value * 2'},
        })

    def test_simple_query(self):
        '''A simple query should use query_string with specified fields'''
        search_query = search.search_for(FakeSearch, q='test')
        expected = {'multi_match': {
            'query': 'test',
            'analyzer': search.i18n_analyzer._name,
            'type': 'cross_fields',
            'fields': ['title^2', 'description']
        }}
        assert_json_equal(get_query(search_query), expected)

    def test_with_multiple_terms(self):
        '''A query with multiple terms should use the AND operator'''
        search_query = search.search_for(FakeSearch, q='test value')
        expected = {'multi_match': {
            'query': 'test value',
            'analyzer': search.i18n_analyzer._name,
            'type': 'cross_fields',
            'operator': 'and',
            'fields': ['title^2', 'description']
        }}
        assert_json_equal(get_query(search_query), expected)

    def test_default_analyzer(self):
        '''Default analyzer is overridable'''
        class FakeAnalyzerSearch(FakeSearch):
            analyzer = 'simple'

        search_query = search.search_for(FakeAnalyzerSearch, q='test')
        expected = {'multi_match': {
            'query': 'test',
            'analyzer': 'simple',
            'type': 'cross_fields',
            'fields': ['title^2', 'description']
        }}
        assert_json_equal(get_query(search_query), expected)

    def test_default_type(self):
        '''Default analyzer is overridable'''
        class FakeAnalyzerSearch(FakeSearch):
            match_type = 'most_fields'

        search_query = search.search_for(FakeAnalyzerSearch, q='test')
        expected = {'multi_match': {
            'query': 'test',
            'analyzer': search.i18n_analyzer._name,
            'type': 'most_fields',
            'fields': ['title^2', 'description']
        }}
        assert_json_equal(get_query(search_query), expected)

    def test_simple_excluding_query(self):
        '''A simple query should negate a simple term in query_string'''
        search_query = search.search_for(FakeSearch, q='-test')
        expected = {
            'bool': {
                'must_not': [
                    {'multi_match': {
                        'query': 'test',
                        'analyzer': search.i18n_analyzer._name,
                        'type': 'cross_fields',
                        'fields': ['title^2', 'description']
                    }}
                ]
            }
        }
        assert_json_equal(get_query(search_query), expected)

    def test_query_with_both_including_and_excluding_terms(self):
        '''A query should detect negation on each term in query_string'''
        search_query = search.search_for(FakeSearch, q='test -negated')
        expected = {
            'bool': {
                'must': [
                    {'multi_match': {
                        'query': 'test',
                        'analyzer': search.i18n_analyzer._name,
                        'type': 'cross_fields',
                        'fields': ['title^2', 'description']
                    }}
                ],
                'must_not': [
                    {'multi_match': {
                        'query': 'negated',
                        'analyzer': search.i18n_analyzer._name,
                        'type': 'cross_fields',
                        'fields': ['title^2', 'description']
                    }}
                ]
            }
        }
        assert_json_equal(get_query(search_query), expected)

    def test_query_with_multiple_including_and_excluding_terms(self):
        '''A query should detect negation on each term in query_string'''
        search_query = search.search_for(FakeSearch,
                                         q='test -negated1 value -negated2')
        expected = {
            'bool': {
                'must': [
                    {'multi_match': {
                        'query': 'test value',
                        'analyzer': search.i18n_analyzer._name,
                        'type': 'cross_fields',
                        'operator': 'and',
                        'fields': ['title^2', 'description']
                    }}
                ],
                'must_not': [
                    {'multi_match': {
                        'query': 'negated1',
                        'analyzer': search.i18n_analyzer._name,
                        'type': 'cross_fields',
                        'fields': ['title^2', 'description']
                    }},
                    {'multi_match': {
                        'query': 'negated2',
                        'analyzer': search.i18n_analyzer._name,
                        'type': 'cross_fields',
                        'fields': ['title^2', 'description']
                    }}
                ]
            }
        }
        assert_json_equal(get_query(search_query), expected)

    def test_simple_query_fuzzy(self):
        '''A simple query should use query_string with specified fields'''
        search_query = search.search_for(FuzzySearch, q='test')
        expected = {'multi_match': {
            'query': 'test',
            'analyzer': search.i18n_analyzer._name,
            'type': 'cross_fields',
            'fields': ['title^2', 'description'],
            'fuzziness': 'AUTO',
            'prefix_length': 2,
        }}
        assert_json_equal(get_query(search_query), expected)

    def test_facets_true(self):
        search_query = search.search_for(FakeSearch, facets=True)
        aggregations = get_body(search_query).get('aggs', {})
        assert len(aggregations) == len(FakeSearch.facets)
        for key in FakeSearch.facets.keys():
            assert key in aggregations.keys()

    def test_facets_all(self):
        search_query = search.search_for(FakeSearch, facets='all')
        aggregations = get_body(search_query).get('aggs', {})
        assert len(aggregations) == len(FakeSearch.facets)
        for key in FakeSearch.facets.keys():
            assert key in aggregations.keys()

    def test_selected_facets(self):
        selected_facets = ['tag', 'other']
        search_query = search.search_for(
            FakeSearch, facets=selected_facets)
        aggregations = get_body(search_query).get('aggs', {})
        assert len(aggregations) == len(selected_facets)
        for key in FakeSearch.facets.keys():
            if key in selected_facets:
                assert key in aggregations.keys()
            else:
                assert key not in aggregations.keys()

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
