# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from bson.objectid import ObjectId
from flask import current_app
from mongoengine.signals import post_save

from udata.core.search.tasks import reindex
from udata.utils import Paginable
from udata.search import es, adapter_catalog, i18n_analyzer, DateRangeFilter, RangeFilter


log = logging.getLogger(__name__)

__all__ = ('ModelSearchAdapter', 'SearchResult', 'multisearch', 'DEFAULT_PAGE_SIZE')

DEFAULT_PAGE_SIZE = 20


def reindex_model(sender, document, **kwargs):
    '''(Re)Index Mongo document on post_save'''
    if current_app.config.get('AUTO_INDEX'):
        reindex.delay(document)


class SearchAdapterMetaClass(type):
    '''Ensure any child class dispatch the signals'''
    def __new__(cls, name, bases, attrs):
        # Ensure any child class dispatch the signals
        adapter = super(SearchAdapterMetaClass, cls).__new__(cls, name, bases, attrs)
        # register the class in the catalog
        if adapter.model:
            adapter_catalog[adapter.model] = adapter
        # Automatically reindex objects on save
        post_save.connect(reindex_model, sender=adapter.model)
        return adapter


class ModelSearchAdapter(object):
    '''This class allow to describe and customize the search behavior for a given model'''
    model = None
    fields = None
    facets = None
    sorts = None
    filters = None
    mapping = None

    __metaclass__ = SearchAdapterMetaClass

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def execute(self):
        try:
            result = es.search(index=es.index_name, doc_type=self.doc_type(), body=self.get_body())
        except:
            result = {}
        return SearchResult(result, self.__class__, **self.kwargs)

    def get_body(self):
        page = max(int(self.kwargs.get('page', 1)), 1)
        page_size = int(self.kwargs.get('page_size', DEFAULT_PAGE_SIZE))
        return {
            'query': self.get_query(),
            'filter': self.get_filter(),
            'facets': self.get_facets(),
            'from': (page - 1) * page_size,
            'size': page_size,
            'sort': self.get_sort(),
            'aggs': self.get_aggregations(),
            'fields': [],  # Only returns IDs
        }

    def get_sort(self):
        '''Build sort query paramter from kwargs'''
        sorts = self.kwargs.get('sort', [])
        sorts = [sorts] if isinstance(sorts, basestring) else sorts
        sorts = [s.split(' ') for s in sorts]
        return [{self.sorts[s].field: d} for s, d in sorts if s in self.sorts]

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
        if self.fields:
            query['multi_match']['fields'] = self.fields
        return [query]

    def build_facet_queries(self):
        '''Build sort query parameters from kwargs'''
        if not self.facets:
            return []
        queries = []
        for name, facet in self.facets.items():
            if name in self.kwargs:
                value = self.kwargs[name]
                for term in [value] if isinstance(value, basestring) else value:
                    queries.append({'term': {facet.field: term}})
        return queries

    def build_filters_queries(self):
        '''Build "must" filter query parameters from kwargs'''
        if not self.filters:
            return []
        queries = []
        ranges = {}
        for name, spec in self.filters.items():
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
            for name, spec in self.filters.items()
            if isinstance(spec, RangeFilter)
        ]
        max_aggs = [
            ('{0}_max'.format(name), {'max': {'field': spec.field}})
            for name, spec in self.filters.items()
            if isinstance(spec, RangeFilter)
        ]
        start_aggs = [
            ('{0}_min'.format(name), {'min': {'field': spec.start_field}})
            for name, spec in self.filters.items()
            if isinstance(spec, DateRangeFilter)
        ]
        end_aggs = [
            ('{0}_max'.format(name), {'max': {'field': spec.end_field}})
            for name, spec in self.filters.items()
            if isinstance(spec, DateRangeFilter)
        ]
        return dict(min_aggs + max_aggs + start_aggs + end_aggs)

    def get_facets(self):
        if not self.facets:
            return {}
        return dict((name, facet.to_query()) for name, facet in self.facets.items())

    def get_query(self):
        must = []
        must.extend(self.build_text_queries())
        must.extend(self.build_facet_queries())
        must.extend(self.build_filters_queries())
        return {'bool': {'must': must}} if must else {'match_all': {}}

    @classmethod
    def doc_type(cls):
        return cls.model.__name__

    @classmethod
    def query(cls, **kwargs):
        return cls(**kwargs).execute()

    @classmethod
    def serialize(cls, document):
        '''By default use the ``to_dict`` method and exclude ``_id``, ``_cls`` and ``owner`` fields'''
        return document.to_dict(exclude=('_id', '_cls', 'owner'))


class SearchResult(Paginable):
    '''An ElasticSearch result wrapper for easy property access'''
    def __init__(self, result, adapter=None, **kwargs):
        self.result = result
        self.adapter = adapter
        self.kwargs = kwargs

    @property
    def total(self):
        return self.result.get('hits', {}).get('total', 0)

    @property
    def max_score(self):
        return self.result.get('hits', {}).get('max_score', 0)

    @property
    def page(self):
        return max(int(self.kwargs.get('page', 1)), 1)

    @property
    def page_size(self):
        return int(self.kwargs.get('page_size', DEFAULT_PAGE_SIZE))

    def get_ids(self):
        return [hit['_id'] for hit in self.result.get('hits', {}).get('hits', [])]

    def get_objects(self):
        ids = [ObjectId(id) for id in self.get_ids()]
        objects = self.adapter.model.objects.in_bulk(ids)
        return [objects.get(id) for id in ids]

    def __iter__(self):
        for obj in self.get_objects():
            yield obj

    def __len__(self):
        return len(self.result.get('hits', {}).get('hits', []))

    def __getitem__(self, index):
        return self.get_objects()[index]

    @property
    def facets(self):
        for name, content in self.result.get('facets', {}).items():
            yield {
                'name': name,
                'terms': [(term['term'], term['count']) for term in content.get('terms', [])],
            }

    def get_facet(self, name):
        if not name in self.adapter.facets or not 'facets' in self.result or not name in self.result['facets']:
            return None
        return {
            'name': name,
            'terms': self.adapter.facets[name].get_values(
                self.result['facets'][name],
                self.kwargs.get(name)
            )
        }

    def get_range(self, name):
        min_name = '{0}_min'.format(name)
        max_name = '{0}_max'.format(name)
        if not name in self.adapter.filters:
            return None
        aggs = self.result.get('aggregations', {})
        if not aggs or not min_name in aggs or not max_name in aggs:
            return None
        spec = self.adapter.filters[name]
        min_value = aggs[min_name]['value'] or 0
        max_value = aggs[max_name]['value'] or 0
        return {
            'min': spec.cast(min_value),
            'max': spec.cast(max_value),
        }


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
