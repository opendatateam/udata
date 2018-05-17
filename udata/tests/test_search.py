# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date, timedelta

import factory

from flask import json
from werkzeug.urls import url_decode, url_parse

from factory.mongoengine import MongoEngineFactory

from elasticsearch_dsl import Q, A
from flask_restplus import inputs
from flask_restplus.reqparse import RequestParser

from udata import search
from udata.core.metrics import Metric
from udata.i18n import gettext as _, format_date
from udata.models import db
from udata.tests import TestCase, DBTestMixin, SearchTestMixin
from udata.utils import faker, clean_string, multi_to_dict


#############################################################################
#                           Fake object for testing                         #
#############################################################################

class Fake(db.Document):
    title = db.StringField()
    description = db.StringField()
    tags = db.ListField(db.StringField())
    other = db.ListField(db.StringField())

    meta = {'allow_inheritance': True}

    def __unicode__(self):
        return self.title

    def __str__(self):
        return self.title

    def __html__(self):
        return '<span>{0}</span>'.format(self.title)


class FakeMetricInt(Metric):
    model = Fake
    name = 'fake-metric-int'


class FakeMetricFloat(Metric):
    model = Fake
    name = 'fake-metric-float'
    value_type = float


class FakeWithStringId(Fake):
    id = db.StringField(primary_key=True)


class FakeFactory(MongoEngineFactory):
    title = factory.Faker('sentence')

    class Meta:
        model = Fake


class FakeWithStringIdFactory(FakeFactory):
    id = factory.Faker('unique_string')

    class Meta:
        model = FakeWithStringId


@search.register
class FakeSearch(search.ModelSearchAdapter):
    class Meta:
        doc_type = 'Fake'

    model = Fake
    fields = [
        'title^2',
        'description',
    ]
    facets = {
        'tag': search.TermsFacet(field='tags'),
        'other': search.TermsFacet(field='other'),
    }
    sorts = {
        'title': 'title.raw',
        'description': 'description.raw',
    }


RANGE_LABELS = {
    'none': _('Never reused'),
    'little': _('Little reused'),
    'quite': _('Quite reused'),
    'heavy': _('Heavily reused'),
}


class FakeSearchWithRange(FakeSearch):
    facets = {
        'range': search.RangeFacet(
            field='a_range_field',
            ranges=[
                ('none', (None, 1)),
                ('little', (1, 5)),
                ('quite', (5, 10)),
                ('heavy', (10, None))
            ],
            labels=RANGE_LABELS
        )
    }


class FakeSearchWithBool(FakeSearch):
    facets = {
        'boolean': search.BoolFacet(field='a_bool_field')
    }


class FakeSearchWithCoverage(FakeSearch):
    facets = {
        'coverage': search.TemporalCoverageFacet(field='a_coverage_field')
    }


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


def es_date(date):
    return float(date.toordinal())


#############################################################################
#                                  Tests                                    #
#############################################################################
class SearchTestCase(TestCase):
    maxDiff = None

    def assert_dict_equal(self, d1, d2, *args, **kwargs):
        d1 = json.loads(json.dumps(d1))
        d2 = json.loads(json.dumps(d2))
        self.assertEqual(d1, d2, *args, **kwargs)


class SearchQueryTest(SearchTestMixin, SearchTestCase):
    def test_execute_search_result(self):
        '''Should return a SearchResult with the right model'''
        self.init_search()
        result = search.query(FakeSearch)
        self.assertIsInstance(result, search.SearchResult)
        self.assertEqual(result.query.adapter, FakeSearch)

    def test_execute_search_result_with_model(self):
        '''Should return a SearchResult with the right model'''
        self.init_search()
        result = search.query(Fake)
        self.assertIsInstance(result, search.SearchResult)
        self.assertEqual(result.query.adapter, FakeSearch)

    def test_should_not_fail_on_missing_objects(self):
        with self.autoindex():
            FakeFactory.create_batch(3)
            deleted_fake = FakeFactory()

        result = search.query(FakeSearch)
        deleted_fake.delete()
        self.assertEqual(len(result), 4)

        # Missing object should be filtered out
        objects = result.objects
        self.assertEqual(len(objects), 3)
        for o in objects:
            self.assertIsInstance(o, Fake)

    def test_only_id(self):
        '''Should only fetch id field'''
        search_query = search.search_for(FakeSearch)
        body = get_body(search_query)
        self.assertEqual(body['fields'], [])

    def test_empty_search(self):
        '''An empty query should match all documents'''
        search_query = search.search_for(FakeSearch)
        body = get_body(search_query)
        self.assertEqual(body['query'], {'match_all': {}})
        self.assertNotIn('aggregations', body)
        self.assertNotIn('aggs', body)
        self.assertNotIn('sort', body)

    def test_paginated_search(self):
        '''Search should handle pagination'''
        search_query = search.search_for(FakeSearch, page=3, page_size=10)
        body = get_body(search_query)
        self.assertIn('from', body)
        self.assertEqual(body['from'], 20)
        self.assertIn('size', body)
        self.assertEqual(body['size'], 10)

    def test_sorted_search_asc(self):
        '''Search should sort by field in ascending order'''
        search_query = search.search_for(FakeSearch, sort='title')
        body = get_body(search_query)
        self.assertEqual(body['sort'], [{'title.raw': 'asc'}])

    def test_sorted_search_desc(self):
        '''Search should sort by field in descending order'''
        search_query = search.search_for(FakeSearch, sort='-title')
        body = get_body(search_query)
        self.assertEqual(body['sort'], [{'title.raw': 'desc'}])

    def test_multi_sorted_search(self):
        '''Search should sort'''
        search_query = search.search_for(FakeSearch,
                                         sort=['-title', 'description'])
        body = get_body(search_query)
        self.assertEqual(body['sort'], [
            {'title.raw': 'desc'},
            {'description.raw': 'asc'},
        ])

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
        self.assertIn('function_score', body['query'])
        self.assertIn('query', body['query']['function_score'])
        self.assertIn('functions', body['query']['function_score'])
        first_function = body['query']['function_score']['functions'][0]
        self.assert_dict_equal(first_function, {
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
        self.assertIn('function_score', body['query'])
        self.assertIn('query', body['query']['function_score'])
        self.assertIn('functions', body['query']['function_score'])
        value_factor = body['query']['function_score']['functions'][0]
        # Should add be field_value_factor with parameter function
        self.assert_dict_equal(value_factor, {
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
        self.assertIn('function_score', body['query'])
        self.assertIn('query', body['query']['function_score'])
        self.assertIn('functions', body['query']['function_score'])
        value_factor = body['query']['function_score']['functions'][0]
        # Should add be field_value_factor with parameter function
        self.assert_dict_equal(value_factor, {
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
        self.assert_dict_equal(functions[0], {
            'gauss': {
                'a_num_field': {
                    'origin': 10,
                    'scale': 10,
                }
            },
        })
        self.assert_dict_equal(functions[1], {
            'exp': {
                'another_field': {
                    'origin': 20,
                    'scale': 20,
                }
            },
        })
        self.assert_dict_equal(functions[2], {
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
        self.assert_dict_equal(functions[0], {
            'gauss': {
                'a_num_field': {
                    'origin': 10,
                    'scale': 20,
                    'offset': 5,
                    'decay': 0.5,
                }
            },
        })
        self.assert_dict_equal(functions[1], {
            'exp': {
                'another_field': {
                    'origin': 20,
                    'scale': 30,
                    'offset': 5,
                    'decay': 0.5,
                }
            },
        })
        self.assert_dict_equal(functions[2], {
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
        self.assert_dict_equal(functions[0], {
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

        query = search.search_for(FakeBoostedSearch)
        body = get_body(query)
        # Query should be wrapped in function_score
        score_function = body['query']['function_score']['functions'][0]
        self.assert_dict_equal(score_function, {
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
        self.assert_dict_equal(get_query(search_query), expected)

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
        self.assert_dict_equal(get_query(search_query), expected)

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
        self.assert_dict_equal(get_query(search_query), expected)

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
        self.assert_dict_equal(get_query(search_query), expected)

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
        self.assert_dict_equal(get_query(search_query), expected)

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
        self.assert_dict_equal(get_query(search_query), expected)

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
        self.assert_dict_equal(get_query(search_query), expected)

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
        self.assert_dict_equal(get_query(search_query), expected)

    def test_facets_true(self):
        search_query = search.search_for(FakeSearch, facets=True)
        aggregations = get_body(search_query).get('aggs', {})
        self.assertEqual(len(aggregations), len(FakeSearch.facets))
        for key in FakeSearch.facets.keys():
            self.assertIn(key, aggregations.keys())

    def test_facets_all(self):
        search_query = search.search_for(FakeSearch, facets='all')
        aggregations = get_body(search_query).get('aggs', {})
        self.assertEqual(len(aggregations), len(FakeSearch.facets))
        for key in FakeSearch.facets.keys():
            self.assertIn(key, aggregations.keys())

    def test_selected_facets(self):
        selected_facets = ['tag', 'other']
        search_query = search.search_for(
            FakeSearch, facets=selected_facets)
        aggregations = get_body(search_query).get('aggs', {})
        self.assertEqual(len(aggregations), len(selected_facets))
        for key in FakeSearch.facets.keys():
            if key in selected_facets:
                self.assertIn(key, aggregations.keys())
            else:
                self.assertNotIn(key, aggregations.keys())

    def test_to_url(self):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
            'facets': True,
        }
        search_query = search.search_for(FakeSearch, **kwargs)
        with self.app.test_request_context('/an_url'):
            url = search_query.to_url()
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        self.assertEqual(parsed_url.path, '/an_url')
        self.assert_dict_equal(multi_to_dict(qs), {
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
        search_query = search.search_for(FakeSearch, **kwargs)
        with self.app.test_request_context('/an_url'):
            url = search_query.to_url(tag='tag3', other='value')
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        self.assertEqual(parsed_url.path, '/an_url')
        self.assert_dict_equal(multi_to_dict(qs), {
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
        search_query = search.search_for(FakeSearch, **kwargs)
        with self.app.test_request_context('/an_url'):
            url = search_query.to_url(tag='tag3', other='value', replace=True)
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        self.assertEqual(parsed_url.path, '/an_url')
        self.assert_dict_equal(multi_to_dict(qs), {
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
        search_query = search.search_for(FakeSearch, **kwargs)
        with self.app.test_request_context('/an_url'):
            url = search_query.to_url(tag=None, other='value', replace=True)
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        self.assertEqual(parsed_url.path, '/an_url')
        self.assert_dict_equal(multi_to_dict(qs), {
            'q': 'test',
            'other': 'value',
        })

    def test_to_url_with_specified_url(self):
        kwargs = {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': 2,
        }
        search_query = search.search_for(FakeSearch, **kwargs)
        with self.app.test_request_context('/an_url'):
            url = search_query.to_url('/another_url')
        parsed_url = url_parse(url)
        qs = url_decode(parsed_url.query)

        self.assertEqual(parsed_url.path, '/another_url')
        self.assert_dict_equal(multi_to_dict(qs), {
            'q': 'test',
            'tag': ['tag1', 'tag2'],
            'page': '2',
        })


class TestMetricsMapping(SearchTestCase):
    def test_map_metrics(self):
        mapping = search.metrics_mapping_for(Fake)
        self.assert_dict_equal(mapping, {
            'type': 'object',
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


def bucket_agg_factory(buckets):
    return {
        'test': {
            'buckets': buckets,
            'doc_count_error_upper_bound': 1,
            'sum_other_doc_count': 94,
        }
    }


def response_factory(nb=20, total=42, **kwargs):
    '''
    Build a fake Elasticsearch DSL FacetedResponse
    and extract the facet form it
    '''
    hits = sorted(
        (hit_factory() for _ in range(nb)),
        key=lambda h: h['_score']
    )
    max_score = hits[-1]['_score']
    data = {
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
    data.update(kwargs)

    return data


class FacetTestCase(TestCase):
    def factory(self, **kwargs):
        '''
        Build a fake Elasticsearch DSL FacetedResponse
        and extract the facet form it
        '''
        data = response_factory(**kwargs)

        class TestSearch(search.SearchQuery):
            facets = {
                'test': self.facet
            }

        s = TestSearch({})
        response = search.SearchResult(s, data)
        return response.facets.test


class TestBoolFacet(FacetTestCase):
    def setUp(self):
        self.facet = search.BoolFacet(field='boolean')

    def test_get_values(self):
        buckets = [
            {'key': 'T', 'doc_count': 10},
            {'key': 'F', 'doc_count': 15},
        ]
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        self.assertEqual(len(result), 2)
        for row in result:
            self.assertIsInstance(row[0], bool)
            self.assertIsInstance(row[1], int)
            self.assertIsInstance(row[2], bool)
        # Assume order is buckets' order
        self.assertTrue(result[0][0])
        self.assertEqual(result[0][1], 10)
        self.assertFalse(result[1][0])
        self.assertEqual(result[1][1], 15)

    def test_value_filter(self):
        for value in True, 'True', 'true':
            expected = Q({'term': {'boolean': True}})
            value_filter = self.facet.get_value_filter(value)
            self.assertEqual(value_filter, expected)

        for value in False, 'False', 'false':
            expected = ~Q({'term': {'boolean': True}})
            value_filter = self.facet.get_value_filter(value)
            self.assertEqual(value_filter, expected)

    def test_aggregation(self):
        expected = A({'terms': {'field': 'boolean'}})
        self.assertEqual(self.facet.get_aggregation(), expected)

    def test_labelize(self):
        self.assertEqual(self.facet.labelize(True), _('yes'))
        self.assertEqual(self.facet.labelize(False), _('no'))

        self.assertEqual(self.facet.labelize('true'), _('yes'))
        self.assertEqual(self.facet.labelize('false'), _('no'))


class TestTermsFacet(FacetTestCase):
    def setUp(self):
        self.facet = search.TermsFacet(field='tags')

    def test_get_values(self):
        buckets = [{
            'key': faker.word(),
            'doc_count': faker.random_number(2)
        } for _ in range(10)]
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        self.assertEqual(len(result), 10)
        for row in result:
            self.assertIsInstance(row[0], basestring)
            self.assertIsInstance(row[1], int)
            self.assertIsInstance(row[2], bool)

    def test_labelize(self):
        self.assertEqual(self.facet.labelize('fake'), 'fake')

    def test_labelize_unicode(self):
        self.assertEqual(self.facet.labelize('é'), 'é')

    def test_labelize_with_or(self):
        self.assertEqual(self.facet.labelize('fake-1|fake-2'),
                         'fake-1 OR fake-2')

    def test_labelize_with_or_and_custom_labelizer(self):
        labelizer = lambda v: 'custom-{0}'.format(v)  # noqa: E731
        facet = search.TermsFacet(field='tags', labelizer=labelizer)
        self.assertEqual(facet.labelize('fake-1|fake-2'),
                         'custom-fake-1 OR custom-fake-2')

    def test_filter_and(self):
        values = ['tag-1', 'tag-2']
        expected = Q('bool', must=[
            Q('term', tags='tag-1'),
            Q('term', tags='tag-2'),
        ])
        self.assertEqual(self.facet.add_filter(values), expected)

    def test_filter_or(self):
        values = ['tag-1|tag-2']
        expected = Q('term', tags='tag-1') | Q('term', tags='tag-2')
        self.assertEqual(self.facet.add_filter(values), expected)

    def test_filter_or_multiple(self):
        values = ['tag-1|tag-2|tag-3']
        expected = Q('bool', should=[
            Q('term', tags='tag-1'),
            Q('term', tags='tag-2'),
            Q('term', tags='tag-3'),
        ])
        self.assertEqual(self.facet.add_filter(values), expected)

    def test_filter_and_or(self):
        values = ['tag-1', 'tag-2|tag-3', 'tag-4|tag-5', 'tag-6']
        expected = Q('bool', must=[
            Q('term', tags='tag-1'),
            Q('term', tags='tag-2') | Q('term', tags='tag-3'),
            Q('term', tags='tag-4') | Q('term', tags='tag-5'),
            Q('term', tags='tag-6'),
        ])
        self.assertEqual(self.facet.add_filter(values), expected)


class TestModelTermsFacet(FacetTestCase, DBTestMixin):
    def setUp(self):
        self.facet = search.ModelTermsFacet(field='fakes', model=Fake)

    def test_labelize_id(self):
        fake = FakeFactory()
        self.assertEqual(
            self.facet.labelize(str(fake.id)), fake.title)

    def test_labelize_object(self):
        fake = FakeFactory()
        self.assertEqual(self.facet.labelize(fake), fake.title)

    def test_labelize_object_with_unicode(self):
        fake = FakeFactory(title='ééé')
        self.assertEqual(self.facet.labelize(fake), 'ééé')

    def test_labelize_object_with_or(self):
        fake_1 = FakeFactory()
        fake_2 = FakeFactory()
        org_facet = search.ModelTermsFacet(field='id', model=Fake)
        self.assertEqual(
            org_facet.labelize('{0}|{1}'.format(fake_1.id, fake_2.id)),
            '{0} OR {1}'.format(fake_1.title, fake_2.title)
        )

    def test_labelize_object_with_or_and_html(self):
        def labelizer(value):
            return Fake.objects(id=value).first()
        fake_1 = FakeFactory()
        fake_2 = FakeFactory()
        facet = search.ModelTermsFacet(field='id', model=Fake,
                                       labelizer=labelizer)
        self.assertEqual(
            facet.labelize('{0}|{1}'.format(fake_1.id, fake_2.id)),
            '<span>{0}</span> OR <span>{1}</span>'.format(fake_1.title,
                                                          fake_2.title)
        )

    def test_get_values(self):
        fakes = [FakeFactory() for _ in range(10)]
        buckets = [{
            'key': str(f.id),
            'doc_count': faker.random_number(2)
        } for f in fakes]
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        self.assertEqual(len(result), 10)
        for fake, row in zip(fakes, result):
            self.assertIsInstance(row[0], Fake)
            self.assertIsInstance(row[1], int)
            self.assertIsInstance(row[2], bool)
            self.assertEqual(fake.id, row[0].id)

    def test_validate_parameters(self):
        fake = FakeFactory()
        for value in [str(fake.id), fake.id]:
            self.assertTrue(self.facet.validate_parameter(value))

        bad_values = ['xyz', True, 42]
        for value in bad_values:
            with self.assertRaises(Exception):
                self.facet.validate_parameter(value)

    def test_validate_parameters_with_or(self):
        fake_1 = FakeFactory()
        fake_2 = FakeFactory()
        value = '{0}|{1}'.format(fake_1.id, fake_2.id)
        self.assertTrue(self.facet.validate_parameter(value))


class TestModelTermsFacetWithStringId(FacetTestCase, DBTestMixin):
    def setUp(self):
        self.facet = search.ModelTermsFacet(field='fakes',
                                            model=FakeWithStringId)

    def test_labelize_id(self):
        fake = FakeWithStringIdFactory()
        self.assertEqual(
            self.facet.labelize(str(fake.id)), fake.title)

    def test_labelize_object(self):
        fake = FakeWithStringIdFactory()
        self.assertEqual(self.facet.labelize(fake), fake.title)

    def test_labelize_object_with_or(self):
        fake_1 = FakeWithStringIdFactory()
        fake_2 = FakeWithStringIdFactory()
        facet = search.ModelTermsFacet(field='id', model=FakeWithStringId)
        self.assertEqual(
            facet.labelize('{0}|{1}'.format(fake_1.id, fake_2.id)),
            '{0} OR {1}'.format(fake_1.title, fake_2.title)
        )

    def test_labelize_object_with_or_and_html(self):
        def labelizer(value):
            return FakeWithStringId.objects(id=value).first()
        fake_1 = FakeWithStringIdFactory()
        fake_2 = FakeWithStringIdFactory()
        facet = search.ModelTermsFacet(field='id', model=FakeWithStringId,
                                       labelizer=labelizer)
        self.assertEqual(
            facet.labelize('{0}|{1}'.format(fake_1.id, fake_2.id)),
            '<span>{0}</span> OR <span>{1}</span>'.format(fake_1.title,
                                                          fake_2.title)
        )

    def test_get_values(self):
        fakes = [FakeWithStringIdFactory() for _ in range(10)]
        buckets = [{
            'key': str(f.id),
            'doc_count': faker.random_number(2)
        } for f in fakes]
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        self.assertEqual(len(result), 10)
        for fake, row in zip(fakes, result):
            self.assertIsInstance(row[0], FakeWithStringId)
            self.assertIsInstance(row[1], int)
            self.assertIsInstance(row[2], bool)
            self.assertEqual(fake.id, row[0].id)

    def test_validate_parameters(self):
        fake = FakeWithStringIdFactory()
        self.assertTrue(self.facet.validate_parameter(fake.id))

    def test_validate_parameters_with_or(self):
        fake_1 = FakeWithStringIdFactory()
        fake_2 = FakeWithStringIdFactory()
        value = '{0}|{1}'.format(fake_1.id, fake_2.id)
        self.assertTrue(self.facet.validate_parameter(value))


class TestRangeFacet(FacetTestCase):
    def setUp(self):
        self.ranges = [
            ('first', (None, 1)),
            ('second', (1, 5)),
            ('third', (5, None))
        ]
        self.facet = search.RangeFacet(
            field='some_field',
            ranges=self.ranges,
            labels={
                'first': 'First range',
                'second': 'Second range',
                'third': 'Third range',
            })

    def buckets(self, first=1, second=2, third=3):
        return [{
            'to': 1.0,
            'to_as_string': '1.0',
            'key': 'first',
            'doc_count': first
        }, {
            'from': 1.0,
            'from_as_string': '1.0',
            'to_as_string': '5.0',
            'key': 'second',
            'doc_count': second
        }, {
            'from_as_string': '5.0',
            'from': 5.0, 'key':
            'third', 'doc_count': third
        }]

    def test_get_values(self):
        buckets = self.buckets()
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        self.assertEqual(len(result), len(self.ranges))
        self.assertEqual(result[0], ('first', 1, False))
        self.assertEqual(result[1], ('second', 2, False))
        self.assertEqual(result[2], ('third', 3, False))

    def test_get_values_with_empty(self):
        buckets = self.buckets(second=0)
        result = self.factory(aggregations=bucket_agg_factory(buckets))

        self.assertEqual(len(result), len(self.ranges) - 1)
        self.assertEqual(result[0], ('first', 1, False))
        self.assertEqual(result[1], ('third', 3, False))

    def test_labelize(self):
        self.assertEqual(self.facet.labelize('first'), 'First range')

    def test_validate_parameters(self):
        for value in self.facet.labels.keys():
            self.assertTrue(self.facet.validate_parameter(value))

        bad_values = ['xyz', True, 45]
        for value in bad_values:
            with self.assertRaises(Exception):
                self.facet.validate_parameter(value)

    def test_labels_ranges_mismatch(self):
        with self.assertRaises(ValueError):
            search.RangeFacet(
                field='some_field',
                ranges=self.ranges,
                labels={
                    'first': 'First range',
                    'second': 'Second range',
                })
        with self.assertRaises(ValueError):
            search.RangeFacet(
                field='some_field',
                ranges=self.ranges,
                labels={
                    'first': 'First range',
                    'second': 'Second range',
                    'unknown': 'Third range',
                })

    def test_get_value_filter(self):
        expected = Q({'range': {
            'some_field': {
                'gte': 1,
                'lt': 5,
            }
        }})
        self.assertEqual(self.facet.get_value_filter('second'), expected)


class TestTemporalCoverageFacet(FacetTestCase):
    def setUp(self):
        self.facet = search.TemporalCoverageFacet(field='some_field')

    def test_get_aggregation(self):
        expected = A({
            'nested': {
                'path': 'some_field'
            },
            'aggs': {
                'min_start': {'min': {'field': 'some_field.start'}},
                'max_end': {'max': {'field': 'some_field.end'}}
            }
        })
        self.assertEqual(self.facet.get_aggregation(), expected)

    def test_get_values(self):
        today = date.today()
        two_days_ago = today - timedelta(days=2, minutes=60)
        result = self.factory(aggregations={'test': {
            'min_start': {'value': float(two_days_ago.toordinal())},
            'max_end': {'value': float(today.toordinal())},
        }})
        self.assertEqual(result['min'], two_days_ago)
        self.assertEqual(result['max'], today)
        self.assertEqual(result['days'], 2.0)

    def test_value_filter(self):
        value_filter = self.facet.get_value_filter('2013-01-07-2014-06-07')
        q_start = Q({'range': {'some_field.start': {
            'lte': date(2014, 6, 7).toordinal(),
        }}})
        q_end = Q({'range': {'some_field.end': {
            'gte': date(2013, 1, 7).toordinal(),
        }}})
        expected = Q('nested', path='some_field', query=q_start & q_end)
        self.assertEqual(value_filter, expected)

    def test_value_filter_reversed(self):
        value_filter = self.facet.get_value_filter('2014-06-07-2013-01-07')
        q_start = Q({'range': {'some_field.start': {
            'lte': date(2014, 6, 7).toordinal(),
        }}})
        q_end = Q({'range': {'some_field.end': {
            'gte': date(2013, 1, 7).toordinal(),
        }}})
        expected = Q('nested', path='some_field', query=q_start & q_end)
        self.assertEqual(value_filter, expected)

    def test_labelize(self):
        label = self.facet.labelize('1940-01-01-2014-12-31')
        expected = '{0} - {1}'.format(
            format_date(date(1940, 1, 1), 'short'),
            format_date(date(2014, 12, 31), 'short')
        )
        self.assertEqual(label, expected)

    def test_validate_parameters(self):
        value = '1940-01-01-2014-12-31'
        self.assertEqual(self.facet.validate_parameter(value), value)

        bad_values = ['xyz', True, 42]
        for value in bad_values:
            with self.assertRaises(ValueError):
                self.facet.validate_parameter(value)


class SearchResultTest(TestCase):
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

        self.assertEqual(result.total, 42)
        self.assertEqual(result.max_score, max_score)

        ids = result.get_ids()
        self.assertEqual(len(ids), 10)

    def test_no_failures(self):
        '''Search result should not fail on missing properties'''
        response = response_factory()
        del response['hits']['total']
        del response['hits']['max_score']
        del response['hits']['hits']
        result = self.factory(response)

        self.assertEqual(result.total, 0)
        self.assertEqual(result.max_score, 0)

        ids = result.get_ids()
        self.assertEqual(len(ids), 0)

    def test_pagination(self):
        '''Search results should be paginated'''
        response = response_factory(nb=3, total=11)
        result = self.factory(response, page=2, page_size=3)

        self.assertEqual(result.page, 2),
        self.assertEqual(result.page_size, 3)
        self.assertEqual(result.pages, 4)

    def test_pagination_empty(self):
        '''Search results should be paginated even if empty'''
        response = response_factory()
        del response['hits']['total']
        del response['hits']['max_score']
        del response['hits']['hits']
        result = self.factory(response, page=2, page_size=3)

        self.assertEqual(result.page, 1),
        self.assertEqual(result.page_size, 3)
        self.assertEqual(result.pages, 0)

    def test_no_pagination_in_query(self):
        '''Search results should be paginated even if not asked'''
        response = response_factory(nb=1, total=1)
        result = self.factory(response)

        self.assertEqual(result.page, 1),
        self.assertEqual(result.page_size, search.DEFAULT_PAGE_SIZE)
        self.assertEqual(result.pages, 1)


class SearchAdaptorTest(SearchTestMixin, TestCase):
    def assert_tokens(self, input, output):
        self.assertEqual(
            set(search.ModelSearchAdapter.completer_tokenize(input)),
            set(output))

    def test_completer_tokenizer(self):
        self.assert_tokens('test', ['test'])
        self.assert_tokens('test square',
                           ['test square', 'test', 'square'])
        self.assert_tokens('test\'s square',
                           ['test\'s square', 'test square', 'test', 'square'])
        self.assert_tokens(
            'test l\'apostrophe',
            ['test l\'apostrophe', 'test apostrophe', 'test', 'apostrophe'])

    def assertHasArgument(self, parser, name, _type, choices=None):
        candidates = [
            arg for arg in parser.args if arg.name == name
        ]
        self.assertEqual(len(candidates), 1,
                         'Should have strictly one argument')
        arg = candidates[0]
        self.assertEqual(arg.type, _type)
        self.assertFalse(arg.required)
        if choices:
            self.assertEqual(set(arg.choices), set(choices))

    def test_as_request_parser_terms_facet(self):
        parser = FakeSearch.as_request_parser()
        self.assertIsInstance(parser, RequestParser)

        # query + facets selector + tag and other facets + sorts + pagination
        self.assertEqual(len(parser.args), 7)
        self.assertHasArgument(parser, 'q', unicode)
        self.assertHasArgument(parser, 'sort', str)
        self.assertHasArgument(parser, 'facets', str)
        self.assertHasArgument(parser, 'tag', clean_string)
        self.assertHasArgument(parser, 'other', clean_string)
        self.assertHasArgument(parser, 'page', int)
        self.assertHasArgument(parser, 'page_size', int)

    def test_as_request_parser_bool_facet(self):
        parser = FakeSearchWithBool.as_request_parser()
        self.assertIsInstance(parser, RequestParser)

        # query + facets selector + boolean facet + sorts + pagination
        self.assertEqual(len(parser.args), 6)
        self.assertHasArgument(parser, 'q', unicode)
        self.assertHasArgument(parser, 'sort', str)
        self.assertHasArgument(parser, 'facets', str)
        self.assertHasArgument(parser, 'boolean', inputs.boolean)
        self.assertHasArgument(parser, 'page', int)
        self.assertHasArgument(parser, 'page_size', int)

    def test_as_request_parser_range_facet(self):
        parser = FakeSearchWithRange.as_request_parser()
        facet = FakeSearchWithRange.facets['range']
        self.assertIsInstance(parser, RequestParser)

        # query + facets selector + range facet + sorts + pagination
        self.assertEqual(len(parser.args), 6)
        self.assertHasArgument(parser, 'q', unicode)
        self.assertHasArgument(parser, 'sort', str)
        self.assertHasArgument(parser, 'facets', str)
        self.assertHasArgument(parser, 'range', facet.validate_parameter,
                               choices=RANGE_LABELS.keys())
        self.assertHasArgument(parser, 'page', int)
        self.assertHasArgument(parser, 'page_size', int)

    def test_as_request_parser_temporal_coverage_facet(self):
        parser = FakeSearchWithCoverage.as_request_parser()
        facet = FakeSearchWithCoverage.facets['coverage']
        self.assertIsInstance(parser, RequestParser)

        # query + facets selector + range facet + sorts + pagination
        self.assertEqual(len(parser.args), 6)
        self.assertHasArgument(parser, 'q', unicode)
        self.assertHasArgument(parser, 'sort', str)
        self.assertHasArgument(parser, 'facets', str)
        self.assertHasArgument(parser, 'coverage', facet.validate_parameter)
        self.assertHasArgument(parser, 'page', int)
        self.assertHasArgument(parser, 'page_size', int)
