# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import time

from datetime import datetime, timedelta, date
from os.path import join, dirname

from werkzeug.urls import url_decode, url_parse

from udata import search
from udata.models import db
from udata.tests import TestCase, DBTestMixin
from udata.tests.factories import faker, MongoEngineFactory
from udata.utils import multi_to_dict

from udata.core.metrics import Metric


class Fake(db.Document):
    INDEX_TYPE = 'fake'
    title = db.StringField()
    description = db.StringField()
    tags = db.ListField(db.StringField())
    other = db.ListField(db.StringField())

    def __unicode__(self):
        return 'fake'


class FakeMetricInt(Metric):
    model = Fake
    name = 'fake-metric-int'


class FakeMetricFloat(Metric):
    model = Fake
    name = 'fake-metric-float'
    value_type = float


class FakeFactory(MongoEngineFactory):
    FACTORY_FOR = Fake


class FakeSearch(search.ModelSearchAdapter):
    model = Fake
    fields = [
        'title^2',
        'description',
    ]
    facets = {
        'tag': search.TermFacet('tags'),
        'other': search.TermFacet('other'),
        'range': search.RangeFacet('a_num_field'),
        'daterange': search.DateRangeFacet('a_daterange_field'),
        'bool': search.BoolFacet('boolean'),
    }
    sorts = {
        'title': search.Sort('title.raw'),
        'description': search.Sort('description.raw'),
    }


class SearchQueryTest(TestCase):
    def test_execute_search_result(self):
        '''SearchQuery execution should return a SearchResult with the right model'''
        result = search.query(FakeSearch)
        self.assertIsInstance(result, search.SearchResult)
        self.assertEqual(result.query.adapter, FakeSearch)

    def test_execute_search_result_with_model(self):
        '''SearchQuery execution from a model should return a SearchResult with the right model'''
        result = search.query(Fake)
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

    def test_facets(self):
        search_query = search.SearchQuery(FakeSearch)
        facets = search_query.get_facets()
        self.assertEqual(len(facets), len(FakeSearch.facets))
        for key in FakeSearch.facets.keys():
            self.assertIn(key, facets.keys())

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
        search_query = search.SearchQuery(FakeSearch, q='test',
            tag=['value-1', 'value-2'],
            other='value',
            range='3-8',
            daterange='2013-01-07-2014-06-07'
        )
        expectations = [
            {'multi_match': {
                'query': 'test',
                'analyzer': search.i18n_analyzer,
                'fields': ['title^2', 'description']
            }},
            {'term': {'tags': 'value-1'}},
            {'term': {'tags': 'value-2'}},
            {'term': {'other': 'value'}},
            {'range': {
                'a_num_field': {
                    'gte': 3,
                    'lte': 8,
                }
            }},
            {'range': {
                'a_daterange_field': {
                    'lte': '2014-06-07',
                    'gte': '2013-01-07',
                },
            }},
        ]
        query = search_query.get_query()
        for expected in expectations:
            self.assertIn(expected, query['bool']['must'])

    def test_to_url(self):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
        }
        search_query = search.SearchQuery(FakeSearch, **kwargs)
        with self.app.test_request_context('/an_url'):
            url = search_query.to_url()
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        self.assertEqual(parsed_url.path, '/an_url')
        self.assertEqual(multi_to_dict(qs), {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': '2',
        })

    def test_to_url_with_override(self):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
        }
        search_query = search.SearchQuery(FakeSearch, **kwargs)
        with self.app.test_request_context('/an_url'):
            url = search_query.to_url(tag='tag3', other='value')
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        self.assertEqual(parsed_url.path, '/an_url')
        self.assertEqual(multi_to_dict(qs), {
            'q': 'test',
            'tag': ['tag1', 'tag2', 'tag3'],
            'other': 'value',
        })

    def test_to_url_with_override_and_replace(self):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
        }
        search_query = search.SearchQuery(FakeSearch, **kwargs)
        with self.app.test_request_context('/an_url'):
            url = search_query.to_url(tag='tag3', other='value', replace=True)
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        self.assertEqual(parsed_url.path, '/an_url')
        self.assertEqual(multi_to_dict(qs), {
            'q': 'test',
            'tag': 'tag3',
            'other': 'value',
        })

    def test_to_url_with_none(self):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
        }
        search_query = search.SearchQuery(FakeSearch, **kwargs)
        with self.app.test_request_context('/an_url'):
            url = search_query.to_url(tag=None, other='value', replace=True)
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        self.assertEqual(parsed_url.path, '/an_url')
        self.assertEqual(multi_to_dict(qs), {
            'q': 'test',
            'other': 'value',
        })

    def test_to_url_with_specified_url(self):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
        }
        search_query = search.SearchQuery(FakeSearch, **kwargs)
        with self.app.test_request_context('/an_url'):
            url = search_query.to_url('/another_url')
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        self.assertEqual(parsed_url.path, '/another_url')
        self.assertEqual(multi_to_dict(qs), {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': '2',
        })


class TestMetricsMapping(TestCase):
    def test_map_metrics(self):
        mapping = search.metrics_mapping(Fake)
        self.assertEqual(mapping, {
            'type': 'object',
            'index_name': 'metrics',
            'properties': {
                'fake-metric-int': {
                    'type': 'integer',
                },
                'fake-metric-float': {
                    'type': 'float',
                },
            }
        })


def hit_factory():
    return {
        "_score": float(faker.random_number(2)),
        "_type": "fake",
        "_id": faker.md5(),
        "_source": {
            "title": faker.sentence(),
            "tags": [faker.word() for _ in range(faker.random_digit())]
        },
        "_index": "udata-test"
    }


def es_factory(nb=20, page=1, page_size=20, total=42):
    '''Build a fake ElasticSearch response'''
    hits = sorted(
        (hit_factory() for _ in range(nb)),
        key=lambda h: h['_score']
    )
    max_score = hits[-1]['_score']
    return {
        "hits": {
            "hits": hits,
            "total": total,
            "max_score": max_score
        },
        "_shards": {
            "successful": 5,
            "failed": 0,
            "total": 5
        },
        "took": 52,
        "timed_out": False
    }


class TestBoolFacet(TestCase):
    def setUp(self):
        self.facet = search.BoolFacet('boolean')

    def test_to_query(self):
        self.assertEqual(self.facet.to_query(), {
            'terms': {
                'field': 'boolean',
                'size': 2,
            }
        })

    def test_from_response(self):
        response = es_factory()
        response['facets'] = {
            'test': {
                '_type': 'terms',
                'total': 229,
                'other': 33,
                'missing': 0,
                'terms': [
                    {'term': True, 'count': 10},
                    {'term': False, 'count': 15},
                ],
            }
        }

        extracted = self.facet.from_response('test', response)
        self.assertEqual(extracted['type'], 'bool')
        self.assertEqual(extracted[True], 10)
        self.assertEqual(extracted[False], 15)

    def test_to_filter(self):
        self.assertEqual(self.facet.to_filter(True), {'term': {'boolean': True}})
        self.assertEqual(self.facet.to_filter('True'), {'term': {'boolean': True}})
        self.assertEqual(self.facet.to_filter('true'), {'term': {'boolean': True}})
        self.assertEqual(self.facet.to_filter(False), {'term': {'boolean': False}})
        self.assertEqual(self.facet.to_filter('False'), {'term': {'boolean': False}})
        self.assertEqual(self.facet.to_filter('false'), {'term': {'boolean': False}})

    def test_aggregations(self):
        self.assertEqual(self.facet.to_aggregations(), {})


class TestTermFacet(TestCase):
    def setUp(self):
        self.facet = search.TermFacet('tags')

    def test_to_query(self):
        self.assertEqual(self.facet.to_query(), {
            'terms': {
                'field': 'tags',
                'size': 10,
            }
        })

    def test_to_query_with_excludes(self):
        self.assertEqual(self.facet.to_query(args=['tag1', 'tag2']), {
            'terms': {
                'field': 'tags',
                'size': 10,
                'exclude': ['tag1', 'tag2']
            }
        })

    def test_from_response(self):
        response = es_factory()
        response['facets'] = {
            'test': {
                '_type': 'terms',
                'total': 229,
                'other': 33,
                'missing': 2,
                'terms': [{'term': faker.word(), 'count': faker.random_number(2)} for _ in range(10)],
            }
        }

        extracted = self.facet.from_response('test', response)
        self.assertEqual(extracted['type'], 'terms')
        self.assertEqual(len(extracted['terms']), 10)

    def test_to_filter(self):
        self.assertEqual(
            self.facet.to_filter('value'),
            {'term': {'tags': 'value'}}
        )

    def test_to_filter_multi(self):
        self.assertEqual(
            self.facet.to_filter(['value1', 'value2']),
            [
                {'term': {'tags': 'value1'}},
                {'term': {'tags': 'value2'}},
            ]
        )

    def test_aggregations(self):
        self.assertEqual(self.facet.to_aggregations(), {})


class TestModelTermFacet(TestCase, DBTestMixin):
    def setUp(self):
        self.facet = search.ModelTermFacet('fakes', Fake)

    def test_to_query(self):
        self.assertEqual(self.facet.to_query(), {
            'terms': {
                'field': 'fakes',
                'size': 10,
            }
        })

    def test_to_query_with_excludes(self):
        self.assertEqual(self.facet.to_query(args=['id1', 'id2']), {
            'terms': {
                'field': 'fakes',
                'size': 10,
                'exclude': ['id1', 'id2']
            }
        })

    def test_labelize(self):
        fake = FakeFactory()
        self.assertEqual(self.facet.labelize(str(fake.id)), 'fake')

    def test_from_response(self):
        fakes = [FakeFactory() for _ in range(10)]
        response = es_factory()
        response['facets'] = {
            'test': {
                '_type': 'terms',
                'total': 229,
                'other': 33,
                'missing': 2,
                'terms': [{'term': str(f.id), 'count': faker.random_number(2)} for f in fakes],
            }
        }

        extracted = self.facet.from_response('test', response)
        self.assertEqual(extracted['type'], 'models')
        self.assertEqual(len(extracted['models']), 10)
        for fake, row in zip(fakes, extracted['models']):
            self.assertIsInstance(row[0], Fake)
            self.assertIsInstance(row[1], int)
            self.assertEqual(fake.id, row[0].id)

    def test_to_filter(self):
        self.assertEqual(self.facet.to_filter('value'), {'term': {'fakes': 'value'}})

    def test_aggregations(self):
        self.assertEqual(self.facet.to_aggregations(), {})


class TestRangeFacet(TestCase):
    def setUp(self):
        self.facet = search.RangeFacet('some_field')

    def test_to_query(self):
        self.assertEqual(self.facet.to_query(), {
            'statistical': {
                'field': 'some_field'
            }
        })

    def test_from_response(self):
        response = es_factory()
        response['facets'] = {
            'test': {
                '_type': 'statistical',
                'count': 123,
                'total': 666,
                'min': 3,
                'max': 42,
                'mean': 21.5,
                'sum_of_squares': 29.0,
                'variance': 2.25,
                'std_deviation': 1.5
            }
        }

        extracted = self.facet.from_response('test', response)
        self.assertEqual(extracted['type'], 'range')
        self.assertEqual(extracted['min'], 3)
        self.assertEqual(extracted['max'], 42)

    def test_from_response_with_error(self):
        response = es_factory()
        response['facets'] = {
            'test': {
                '_type': 'statistical',
                'count': 0,
                'total': 0,
                'min': 'Infinity',
                'max': '-Infinity',
                'mean': 0.0,
                'sum_of_squares': 0.0,
                'variance': 'NaN',
                'std_deviation': 'NaN'
            }
        }

        extracted = self.facet.from_response('test', response)
        self.assertEqual(extracted['type'], 'range')
        self.assertEqual(extracted['min'], None)
        self.assertEqual(extracted['max'], None)
        self.assertFalse(extracted['visible'])

    def test_to_filter(self):
        self.assertEqual(self.facet.to_filter('3-8'), {
            'range': {
                'some_field': {
                    'gte': 3,
                    'lte': 8,
                }
            }
        })

    def test_aggregations(self):
        self.assertEqual(self.facet.to_aggregations(), {})


class TestDateRangeFacet(TestCase):
    def setUp(self):
        self.facet = search.DateRangeFacet('some_field')

    def _es_timestamp(self, dt):
        return time.mktime(dt.timetuple()) * 1E3

    def test_to_query(self):
        self.assertEqual(self.facet.to_query(), {
            'statistical': {
                'field': 'some_field'
            }
        })

    def test_from_response(self):
        now = datetime.now()
        two_days_ago = now - timedelta(days=2)
        response = es_factory()
        response['facets'] = {
            'test': {
                '_type': 'statistical',
                'count': 123,
                'total': 666,
                'min': self._es_timestamp(two_days_ago),
                'max': self._es_timestamp(now),
                'mean': 21.5,
                'sum_of_squares': 29.0,
                'variance': 2.25,
                'std_deviation': 1.5
            }
        }

        extracted = self.facet.from_response('test', response)
        self.assertEqual(extracted['type'], 'daterange')
        self.assertEqual(extracted['min'], two_days_ago.replace(microsecond=0))
        self.assertEqual(extracted['max'], now.replace(microsecond=0))

    def test_to_filter(self):
        self.assertEqual(self.facet.to_filter('2013-01-07-2014-06-07'), {
            'range': {
                'some_field': {
                    'lte': '2014-06-07',
                    'gte': '2013-01-07',
                },
            }
        })

    def test_aggregations(self):
        self.assertEqual(self.facet.to_aggregations(), {})


class TestTemporalCoverageFacet(TestCase):
    def setUp(self):
        self.facet = search.TemporalCoverageFacet('some_field')

    def test_to_query(self):
        self.assertIsNone(self.facet.to_query())

    def test_to_aggregations(self):
        aggregations = self.facet.to_aggregations()
        self.assertEqual(aggregations['some_field_min'], {'min': {'field': 'some_field.start'}})
        self.assertEqual(aggregations['some_field_max'], {'max': {'field': 'some_field.end'}})

    def test_from_response(self):
        today = date.today()
        two_days_ago = today - timedelta(days=2)
        response = es_factory()
        response['aggregations'] = {
            'some_field_min': {'value': float(two_days_ago.toordinal())},
            'some_field_max': {'value': float(today.toordinal())},
        }

        extracted = self.facet.from_response('test', response)
        self.assertEqual(extracted['type'], 'temporal-coverage')
        self.assertEqual(extracted['min'], two_days_ago)
        self.assertEqual(extracted['max'], today)

    def test_to_filter(self):
        self.assertEqual(self.facet.to_filter('2013-01-07-2014-06-07'), [{
            'range': {
                'some_field.start': {
                    'lte': date(2014, 6, 7).toordinal(),
                },
            }
        }, {
            'range': {
                'some_field.end': {
                    'gte': date(2013, 1, 7).toordinal(),
                },
            }
        }])


class SearchResultTest(TestCase):
    def load_result(self, filename):
        with open(join(dirname(__file__), filename)) as result:
            return json.load(result)

    def test_properties(self):
        '''Search result should map some properties for easy access'''
        response = es_factory(nb=10, total=42)
        max_score = response['hits']['max_score']
        query = search.SearchQuery(FakeSearch)
        result = search.SearchResult(query, response)

        self.assertEqual(result.total, 42)
        self.assertEqual(result.max_score, max_score)

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
        result = search.SearchResult(query, es_factory(nb=3, total=11))

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
