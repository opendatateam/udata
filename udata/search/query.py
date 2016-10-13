# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import logging

from functools import partial

from flask import request
from werkzeug.urls import Href

from elasticsearch_dsl import Search, FacetedSearch, Q

from udata.search import es, DEFAULT_PAGE_SIZE
from udata.search.result import SearchResult


log = logging.getLogger(__name__)


class SearchQuery(FacetedSearch):
    model = None
    adapter = None
    analyzer = None
    match_type = None
    fuzzy = False

    def __init__(self, params):
        self.extract_sort(params)
        self.extract_pagination(params)
        q = params.pop('q', '')
        super(SearchQuery, self).__init__(q, params)
        # Until https://github.com/elastic/elasticsearch-dsl-py/pull/474
        # is merged and released
        self._s = self._s.fields([])

    def extract_sort(self, params):
        '''Extract and build sort query from parameters'''
        sorts = params.pop('sort', [])
        sorts = [sorts] if isinstance(sorts, basestring) else sorts
        sorts = [(s[1:], 'desc')
                 if s.startswith('-') else (s, 'asc')
                 for s in sorts]
        self.sorts = [
            {self.adapter.sorts[s]: d}
            for s, d in sorts if s in self.adapter.sorts
        ]

    def extract_pagination(self, params):
        '''Extract and build pagination from parameters'''
        try:
            params_page = int(params.pop('page', 1) or 1)
            self.page = max(params_page, 1)
        except:
            # Failsafe, if page cannot be parsed, we falback on first page
            self.page = 1
        try:
            params_page_size = params.pop('page_size', DEFAULT_PAGE_SIZE)
            self.page_size = int(params_page_size or DEFAULT_PAGE_SIZE)
        except:
            # Failsafe, if page_size cannot be parsed, we falback on default
            self.page_size = DEFAULT_PAGE_SIZE
        self.page_start = (self.page - 1) * self.page_size
        self.page_end = self.page_start + self.page_size

    def aggregate(self, search):
        """
        Add aggregations representing the facets selected
        """
        for f, facet in self.facets.items():
            agg = facet.get_aggregation()
            search.aggs.bucket(f, agg)

    def filter(self, search):
        '''
        Perform filtering instead of default post-filtering.
        '''
        if not self._filters:
            return search
        filters = Q('match_all')
        for f in self._filters.values():
            filters &= f
        return search.filter(filters)

    def search(self):
        """
        Construct the Search object.
        """
        s = Search(doc_type=self.doc_types, using=es.client, index=es.index_name)
        # don't return any fields, just the metadata
        s = s.fields([])
        # Sort from parameters
        s = s.sort(*self.sorts)
        # Paginate from parameters
        s = s[self.page_start:self.page_end]
        # Same construction as parent class
        # Allows to give the same signature as simple search
        # ie. Response(data) instead of Response(search, data)
        return s.response_class(partial(SearchResult, self))

    def query(self, search, query):
        """
        Add query part to ``search``.

        Override this if you wish to customize the query used.
        """
        if not query:
            return search
        params = {'query': query}
        # Optionnal search type
        if self.match_type:
            params['type'] = self.match_type
        # Optionnal analyzer
        if self.analyzer:
            params['analyzer'] = self.analyzer
        # Optionnal fuzzines
        if self.fuzzy:
            params['fuzziness'] = 'AUTO'
            params['prefix_length'] = 2  # Make it configurable ?
        return search.query('multi_match', fields=self.fields, **params)

    def to_url(self, url=None, replace=False, **kwargs):
        '''Serialize the query into an URL'''
        params = copy.deepcopy(self.filter_values)
        if self._query:
            params['q'] = self._query
        if self.page_size != DEFAULT_PAGE_SIZE:
            params['page_size'] = self.page_size
        if kwargs:
            for key, value in kwargs.items():
                if not replace and key in params:
                    if not isinstance(params[key], (list, tuple)):
                        params[key] = [params[key], value]
                    else:
                        params[key].append(value)
                else:
                    params[key] = value
        else:
            params['page'] = self.page
        href = Href(url or request.base_url)
        return href(params)
