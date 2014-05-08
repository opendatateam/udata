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
        result = FakeSearch.query()
        self.assertIsInstance(result, search.SearchResult)
        self.assertEqual(result.adapter, FakeSearch)

    def test_empty_search(self):
        '''An empty query should match all documents'''
        fake_search = FakeSearch()
        expected = {'match_all': {}}
        self.assertEqual(fake_search.get_query(), expected)

    def test_paginated_search(self):
        '''Search should handle pagination'''
        fake_search = FakeSearch(page=3, page_size=10)
        body = fake_search.get_body()
        self.assertIn('from', body)
        self.assertEqual(body['from'], 20)
        self.assertIn('size', body)
        self.assertEqual(body['size'], 10)

    def test_sorted_search_asc(self):
        '''Search should sort by field in ascending order'''
        fake_search = FakeSearch(sort='title')
        body = fake_search.get_body()
        self.assertEqual(body['sort'], [{'title.raw': 'asc'}])

    def test_sorted_search_desc(self):
        '''Search should sort by field in descending order'''
        fake_search = FakeSearch(sort='-title')
        body = fake_search.get_body()
        self.assertEqual(body['sort'], [{'title.raw': 'desc'}])

    def test_multi_sorted_search(self):
        '''Search should sort'''
        fake_search = FakeSearch(sort=['-title', 'description'])
        body = fake_search.get_body()
        self.assertEqual(body['sort'], [
            {'title.raw': 'desc'},
            {'description.raw': 'asc'},
        ])

    def test_simple_query(self):
        '''A simple query should use query_string with specified fields'''
        fake_search = FakeSearch(q='test')
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
        self.assertEqual(fake_search.get_query(), expected)

    def test_simple_query_flatten(self):
        '''A simple query should use query_string with specified fields and should flatten'''
        fake_search = FakeSearch(q='test')
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
        self.assertEqual(fake_search.get_query(), expected)

    def test_term_facet(self):
        fake_search = FakeSearch()
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
        self.assertEqual(fake_search.get_facets(), expected)

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
        fake_search = FakeSearch(q='test', tag='value')
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
        self.assertEqual(fake_search.get_query(), expected)

    def test_facet_filter_multi(self):
        fake_search = FakeSearch(q='test', tag=['value-1', 'value-2'], other='value')
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
        self.assertEqual(fake_search.get_query(), expected)

    def test_range_filter(self):
        fake_search = FakeSearch(myrange='3-7.5')
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
        self.assertEqual(fake_search.get_query(), expected)

    def test_range_min_max(self):
        fake_search = FakeSearch()

        aggregations = fake_search.get_aggregations()

        self.assertEqual(aggregations['myrange_min'], {'min': {'field': 'numeric_field'}})
        self.assertEqual(aggregations['myrange_max'], {'max': {'field': 'numeric_field'}})

    def test_daterange_filter(self):
        fake_search = FakeSearch(daterange='2013-01-07-2014-06-07')
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
        self.assertEqual(fake_search.get_query(), expected)

    def test_daterange_min_max(self):
        fake_search = FakeSearch()

        aggregations = fake_search.get_aggregations()

        self.assertEqual(aggregations['daterange_min'], {'min': {'field': 'daterange_start'}})
        self.assertEqual(aggregations['daterange_max'], {'max': {'field': 'daterange_end'}})

    def test_bool_filter_true(self):
        fake_search = FakeSearch(bool_filter=True)
        expected = {'bool': {
            'must': [
                {'term': {'bool_filter_field': True}}
            ]
        }}
        self.assertEqual(fake_search.get_query(), expected)

    def test_bool_filter_false(self):
        fake_search = FakeSearch(bool_filter=False)
        expected = {'bool': {
            'must': [
                {'term': {'bool_filter_field': False}}
            ]
        }}
        self.assertEqual(fake_search.get_query(), expected)


class SearchResultTest(TestCase):
    def load_result(self, filename):
        with open(join(dirname(__file__), filename)) as result:
            return json.load(result)

    def test_properties(self):
        '''Search result should map some properties for easy access'''
        fixture = self.load_result('es-fake-result.json')
        result = search.SearchResult(fixture, FakeSearch)

        self.assertEqual(result.total, 42)
        self.assertEqual(result.max_score, 10.0)

        ids = result.get_ids()
        self.assertEqual(len(ids), 10)

    def test_no_failures(self):
        '''Search result should not fail on missing properties'''
        result = search.SearchResult({}, FakeSearch)

        self.assertEqual(result.total, 0)
        self.assertEqual(result.max_score, 0)

        ids = result.get_ids()
        self.assertEqual(len(ids), 0)

    def test_pagination(self):
        '''Search results should be paginated'''
        kwargs = {'page': 2, 'page_size': 3}
        result = search.SearchResult({'hits': {'total': 11}}, FakeSearch, **kwargs)

        self.assertEqual(result.page, 2),
        self.assertEqual(result.page_size, 3)
        self.assertEqual(result.pages, 4)

    def test_pagination_empty(self):
        '''Search results should be paginated even if empty'''
        result = search.SearchResult({}, FakeSearch)

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
        result = search.SearchResult(es_result, FakeSearch)

        range = result.get_range('myrange')
        self.assertEqual(range['min'], 3.0)
        self.assertIsInstance(range['min'], float)
        self.assertEqual(range['max'], 35.0)
        self.assertIsInstance(range['max'], float)

