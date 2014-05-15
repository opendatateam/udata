# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from bson.objectid import ObjectId

from udata.search import es, i18n_analyzer, DEFAULT_PAGE_SIZE
from udata.search.fields import DateRangeFilter, RangeFilter
from udata.search.result import SearchResult


log = logging.getLogger(__name__)


class SearchQuery(object):
    '''
    This wraps an ElasticSearch query
    '''

    def __init__(self, *adapters, **kwargs):
        self.adapter = adapters[0]
        self.adapters = adapters
        self.kwargs = kwargs

        self.page = max(int(self.kwargs.get('page', 1)), 1)
        self.page_size = int(self.kwargs.get('page_size', DEFAULT_PAGE_SIZE))

    def execute(self):
        try:
            result = es.search(index=es.index_name, doc_type=self.adapter.doc_type(), body=self.get_body())
        except:
            result = {}
        return SearchResult(self, result)

    def get_body(self):
        body = {
            'filter': self.get_filter(),
            'facets': self.get_facets(),
            'from': (self.page - 1) * self.page_size,
            'size': self.page_size,
            'sort': self.get_sort(),
            'aggs': self.get_aggregations(),
            'fields': [],  # Only returns IDs
        }
        if hasattr(self.adapter, 'boosters') and self.adapter.boosters:
            body['query'] = {
                'function_score': {
                    'query': self.get_query(),
                    'functions': self.get_score_functions(),
                }
            }
        else:
            body['query'] = self.get_query()

        return body

    def get_score_functions(self):
        return [b.to_query() for b in self.adapter.boosters]

    def get_sort(self):
        '''Build sort query paramter from kwargs'''
        sorts = self.kwargs.get('sort', [])
        sorts = [sorts] if isinstance(sorts, basestring) else sorts
        sorts = [(s[1:], 'desc') if s.startswith('-') else  (s, 'asc') for s in sorts]
        return [
            {self.adapter.sorts[s].field: d}
            for s, d in sorts if s in self.adapter.sorts
        ]

    def get_filter(self):
        return {}

    def build_text_queries(self):
        '''Build full text query from kwargs'''
        if not self.kwargs.get('q'):
            return []
        query_string = self.kwargs.get('q')
        if isinstance(query_string, (list, tuple)):
            query_string = ' '.join(query_string)
        query = {'multi_match': {'query': query_string, 'analyzer': i18n_analyzer}}
        if self.adapter.fields:
            query['multi_match']['fields'] = self.adapter.fields
        return [query]

    def build_facet_queries(self):
        '''Build sort query parameters from kwargs'''
        if not self.adapter.facets:
            return []
        queries = []
        for name, facet in self.adapter.facets.items():
            if name in self.kwargs:
                value = self.kwargs[name]
                for term in [value] if isinstance(value, basestring) else value:
                    queries.append({'term': {facet.field: term}})
        return queries

    def build_filters_queries(self):
        '''Build "must" filter query parameters from kwargs'''
        if not self.adapter.filters:
            return []
        queries = []
        ranges = {}
        for name, spec in self.adapter.filters.items():
            if name in self.kwargs:
                if isinstance(spec, (RangeFilter, DateRangeFilter)):
                    ranges.update(spec.to_query(self.kwargs[name]))
                else:
                    queries.append(spec.to_query(self.kwargs[name]))
        if ranges:
            queries.append({'range': ranges})
        return queries

    def get_aggregations(self):
        min_aggs = [
            ('{0}_min'.format(name), {'min': {'field': spec.field}})
            for name, spec in self.adapter.filters.items()
            if isinstance(spec, RangeFilter)
        ]
        max_aggs = [
            ('{0}_max'.format(name), {'max': {'field': spec.field}})
            for name, spec in self.adapter.filters.items()
            if isinstance(spec, RangeFilter)
        ]
        start_aggs = [
            ('{0}_min'.format(name), {'min': {'field': spec.start_field}})
            for name, spec in self.adapter.filters.items()
            if isinstance(spec, DateRangeFilter)
        ]
        end_aggs = [
            ('{0}_max'.format(name), {'max': {'field': spec.end_field}})
            for name, spec in self.adapter.filters.items()
            if isinstance(spec, DateRangeFilter)
        ]
        return dict(min_aggs + max_aggs + start_aggs + end_aggs)

    def get_facets(self):
        if not self.adapter.facets:
            return {}
        return dict((name, facet.to_query()) for name, facet in self.adapter.facets.items())

    def get_query(self):
        must = []
        must.extend(self.build_text_queries())
        must.extend(self.build_facet_queries())
        must.extend(self.build_filters_queries())
        return {'bool': {'must': must}} if must else {'match_all': {}}


def multisearch(*adapters):
    body = []
    for adapter in adapters:
        body.append({'type': adapter.doc_type()})
        body.append(adapter.get_body())
    try:
        result = es.msearch(index=es.index_name, body=body)
    except:
        result = [{} for _ in range(len(adapters))]
    return [
        SearchResult(response, adapter.__class__, **adapter.kwargs)
        for response, adapter in zip(result['responses'], adapters)
    ]
