# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from os.path import join, dirname

from udata import search
from udata.models import db
from udata.tests import TestCase


class Fake(db.Document):
    INDEX_TYPE = 'fake'
    title = db.StringField()
    description = db.StringField()
    tags = db.ListField(db.StringField())
    other = db.ListField(db.StringField())


class FakeSearch(search.ModelSearchAdapter):
    model = Fake
    fields = [
        'title^2',
        'description',
    ]
    facets = {
        'tag': search.TermFacet('tags'),
        'other': search.TermFacet('other'),
    }
    sorts = {
        'title': search.Sort('title.raw'),
        'description': search.Sort('description.raw'),
    }
    filters = {
        'myrange': search.RangeFilter('numeric_field', float),
        'daterange': search.DateRangeFilter('daterange_start', 'daterange_end'),
        'bool_filter': search.BoolFilter('bool_filter_field'),
    }


class SearchQueryTest(TestCase):
    def test_execute_search_result(self):
        '''SearchQuery execution should return a SearchResult with the right model'''
        # query = FakeSearchQuery()
        result = search.query(FakeSearch)
        self.assertIsInstance(result, search.SearchResult)
        self.assertEqual(result.query.adapter, FakeSearch)

    def test_empty_search(self):
        '''An empty query should match all documents'''
        search_query = search.SearchQuery(FakeSearch)
        expected = {'match_all': {}}
        self.assertEqual(search_query.get_query(), expected)

    def test_paginated_search(self):
        '''Search should handle pagination'''
        search_query = search.SearchQuery(FakeSearch, page=3, page_size=10)
        body = search_query.get_body()
        self.assertIn('from', body)
        self.assertEqual(body['from'], 20)
        self.assertIn('size', body)
        self.assertEqual(body['size'], 10)

    def test_sorted_search_asc(self):
        '''Search should sort by field in ascending order'''
        search_query = search.SearchQuery(FakeSearch, sort='title')
        body = search_query.get_body()
        self.assertEqual(body['sort'], [{'title.raw': 'asc'}])

    def test_sorted_search_desc(self):
        '''Search should sort by field in descending order'''
        search_query = search.SearchQuery(FakeSearch, sort='-title')
        body = search_query.get_body()
        self.assertEqual(body['sort'], [{'title.raw': 'desc'}])

    def test_multi_sorted_search(self):
        '''Search should sort'''
        search_query = search.SearchQuery(FakeSearch, sort=['-title', 'description'])
        body = search_query.get_body()
        self.assertEqual(body['sort'], [
            {'title.raw': 'desc'},
            {'description.raw': 'asc'},
        ])

    def test_custom_scoring(self):
        '''Search should handle field boosting'''
        class FakeBoostedSearch(FakeSearch):
            boosters = [
                search.BoolBooster('some_bool_field', 1.1)
            ]

        query = search.SearchQuery(FakeBoostedSearch)
        body = query.get_body()
        # Query should be wrapped in function_score
        self.assertIn('function_score', body['query'])
        self.assertIn('query', body['query']['function_score'])
        self.assertIn('functions', body['query']['function_score'])
        self.assertEqual(body['query']['function_score']['functions'][0], {
            'filter': {'term': {'some_bool_field': True}},
            'boost_factor': 1.1,
        })

    def test_decay_function_scoring(self):
        '''Search should handle field decay'''
        class FakeBoostedSearch(FakeSearch):
            boosters = [
                search.GaussDecay('a_num_field', 10),
                search.ExpDecay('another_field', 20),
                search.LinearDecay('last_field', 30),
            ]

        query = search.SearchQuery(FakeBoostedSearch)
        body = query.get_body()
        functions = body['query']['function_score']['functions']
        # Query should be wrapped in a gaus decay function
        self.assertEqual(functions[0], {
            'gauss': {
                'a_num_field': {
                    'origin': 10,
                    'scale': 10,
                }
            },
        })
        self.assertEqual(functions[1], {
            'exp': {
                'another_field': {
                    'origin': 20,
                    'scale': 20,
                }
            },
        })
        self.assertEqual(functions[2], {
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
                search.ExpDecay('another_field', 20, scale=30, offset=5, decay=0.5),
                search.LinearDecay('last_field', 30, 40, offset=5, decay=0.5),
            ]

        query = search.SearchQuery(FakeBoostedSearch)
        body = query.get_body()
        functions = body['query']['function_score']['functions']
        # Query should be wrapped in a gaus decay function
        self.assertEqual(functions[0], {
            'gauss': {
                'a_num_field': {
                    'origin': 10,
                    'scale': 20,
                    'offset': 5,
                    'decay': 0.5,
                }
            },
        })
        self.assertEqual(functions[1], {
            'exp': {
                'another_field': {
                    'origin': 20,
                    'scale': 30,
                    'offset': 5,
                    'decay': 0.5,
                }
            },
        })
        self.assertEqual(functions[2], {
            'linear': {
                'last_field': {
                    'origin': 30,
                    'scale': 40,
                    'offset': 5,
                    'decay': 0.5
                }
            },
        })

    def test_custom_function_scoring(self):
        '''Search should handle field boosting by function'''
        class FakeBoostedSearch(FakeSearch):
            boosters = [
                search.FunctionBooster('doc["field"].value * 2')
            ]

        query = search.SearchQuery(FakeBoostedSearch)
        body = query.get_body()
        # Query should be wrapped in function_score
        self.assertEqual(body['query']['function_score']['functions'][0], {
            'script_score': {'script': 'doc["field"].value * 2'},
        })

    def test_simple_query(self):
        '''A simple query should use query_string with specified fields'''
        search_query = search.SearchQuery(FakeSearch, q='test')
        expected = {
            'bool': {
                'must': [
                    {'multi_match': {
                        'query': 'test',
                        'analyzer': search.i18n_analyzer,
                        'fields': ['title^2', 'description']
                    }}
                ]
            }
        }
        self.assertEqual(search_query.get_query(), expected)

    def test_simple_query_flatten(self):
        '''A simple query should use query_string with specified fields and should flatten'''
        search_query = search.SearchQuery(FakeSearch, q='test')
        expected = {
            'bool': {
                'must': [
                    {'multi_match': {
                        'query': 'test',
                        'analyzer': search.i18n_analyzer,
                        'fields': ['title^2', 'description']
                    }}
                ]
            }
        }
        self.assertEqual(search_query.get_query(), expected)

    def test_term_facet(self):
        search_query = search.SearchQuery(FakeSearch, )
        expected = {
            'tag': {
                'terms': {
                    'field': 'tags',
                    'size': 10,
                }
            },
            'other': {
                'terms': {
                    'field': 'other',
                    'size': 10,
                }
            },
        }
        self.assertEqual(search_query.get_facets(), expected)

    def test_range_facet(self):
        facet = search.RangeFacet('some_field', [
            {'to': 10},
            {'from': 10, 'to': 50},
            {'from': 50, 'to': 100},
            {'from': 100},
        ])

        self.assertEqual(facet.to_query(), {
            'range': {
                'field': 'some_field',
                'ranges': [
                    {'to': 10},
                    {'from': 10, 'to': 50},
                    {'from': 50, 'to': 100},
                    {'from': 100}
                ]
            }
        })

    def test_facet_filter(self):
        search_query = search.SearchQuery(FakeSearch, q='test', tag='value')
        expected = {
            'bool': {
                'must': [
                    {'multi_match': {
                        'query': 'test',
                        'analyzer': search.i18n_analyzer,
                        'fields': ['title^2', 'description']
                    }},
                    {'term': {'tags': 'value'}},
                ]
            }
        }
        self.assertEqual(search_query.get_query(), expected)

    def test_facet_filter_multi(self):
        search_query = search.SearchQuery(FakeSearch, q='test', tag=['value-1', 'value-2'], other='value')
        expected = {
            'bool': {
                'must': [
                    {'multi_match': {
                        'query': 'test',
                        'analyzer': search.i18n_analyzer,
                        'fields': ['title^2', 'description']
                    }},
                    {'term': {'tags': 'value-1'}},
                    {'term': {'tags': 'value-2'}},
                    {'term': {'other': 'value'}},
                ]
            }
        }
        self.assertEqual(search_query.get_query(), expected)

    def test_range_filter(self):
        search_query = search.SearchQuery(FakeSearch, myrange='3-7.5')
        expected = {
            'bool': {
                'must': [
                    {'range': {
                        'numeric_field': {
                            'gte': 3.0,
                            'lte': 7.5,
                        }
                    }}
                ]
            }
        }
        self.assertEqual(search_query.get_query(), expected)

    def test_range_min_max(self):
        search_query = search.SearchQuery(FakeSearch, )

        aggregations = search_query.get_aggregations()

        self.assertEqual(aggregations['myrange_min'], {'min': {'field': 'numeric_field'}})
        self.assertEqual(aggregations['myrange_max'], {'max': {'field': 'numeric_field'}})

    def test_daterange_filter(self):
        search_query = search.SearchQuery(FakeSearch, daterange='2013-01-07-2014-06-07')
        expected = {
            'bool': {
                'must': [
                    {'range': {
                        'daterange_start': {
                            'lte': '2014-06-07',
                        },
                        'daterange_end': {
                            'gte': '2013-01-07',
                        },
                    }}
                ]
            }
        }
        self.assertEqual(search_query.get_query(), expected)

    def test_daterange_min_max(self):
        search_query = search.SearchQuery(FakeSearch, )

        aggregations = search_query.get_aggregations()

        self.assertEqual(aggregations['daterange_min'], {'min': {'field': 'daterange_start'}})
        self.assertEqual(aggregations['daterange_max'], {'max': {'field': 'daterange_end'}})

    def test_bool_filter_true(self):
        search_query = search.SearchQuery(FakeSearch, bool_filter=True)
        expected = {'bool': {
            'must': [
                {'term': {'bool_filter_field': True}}
            ]
        }}
        self.assertEqual(search_query.get_query(), expected)

    def test_bool_filter_false(self):
        search_query = search.SearchQuery(FakeSearch, bool_filter=False)
        expected = {'bool': {
            'must': [
                {'term': {'bool_filter_field': False}}
            ]
        }}
        self.assertEqual(search_query.get_query(), expected)


class SearchResultTest(TestCase):
    def load_result(self, filename):
        with open(join(dirname(__file__), filename)) as result:
            return json.load(result)

    def test_properties(self):
        '''Search result should map some properties for easy access'''
        fixture = self.load_result('es-fake-result.json')
        query = search.SearchQuery(FakeSearch)
        result = search.SearchResult(query, fixture)

        self.assertEqual(result.total, 42)
        self.assertEqual(result.max_score, 10.0)

        ids = result.get_ids()
        self.assertEqual(len(ids), 10)

    def test_no_failures(self):
        '''Search result should not fail on missing properties'''
        query = search.SearchQuery(FakeSearch)
        result = search.SearchResult(query, {})

        self.assertEqual(result.total, 0)
        self.assertEqual(result.max_score, 0)

        ids = result.get_ids()
        self.assertEqual(len(ids), 0)

    def test_pagination(self):
        '''Search results should be paginated'''
        kwargs = {'page': 2, 'page_size': 3}
        query = search.SearchQuery(FakeSearch, **kwargs)
        result = search.SearchResult(query, {'hits': {'total': 11}})

        self.assertEqual(result.page, 2),
        self.assertEqual(result.page_size, 3)
        self.assertEqual(result.pages, 4)

    def test_pagination_empty(self):
        '''Search results should be paginated even if empty'''
        query = search.SearchQuery(FakeSearch)
        result = search.SearchResult(query, {})

        self.assertEqual(result.page, 1),
        self.assertEqual(result.page_size, search.DEFAULT_PAGE_SIZE)
        self.assertEqual(result.pages, 0)

    def test_get_range(self):
        '''Search result should give access to range boundaries'''
        es_result = {
            'aggregations': {
                'myrange_min': {'value': 3},
                'myrange_max': {'value': 35},
            }
        }
        query = search.SearchQuery(FakeSearch)
        result = search.SearchResult(query, es_result)

        range = result.get_range('myrange')
        self.assertEqual(range['min'], 3.0)
        self.assertIsInstance(range['min'], float)
        self.assertEqual(range['max'], 35.0)
        self.assertIsInstance(range['max'], float)
