import copy
import logging

from functools import partial

from flask import request
from werkzeug.urls import Href

from elasticsearch_dsl import Search, FacetedSearch, Q
from elasticsearch_dsl.aggs import Bucket, Pipeline
from elasticsearch_dsl.query import FunctionScore

from udata.search import es, DEFAULT_PAGE_SIZE
from udata.search.result import SearchResult


log = logging.getLogger(__name__)


class SearchQuery(FacetedSearch):
    adapter = None
    analyzer = None
    boosters = None
    fuzzy = False
    match_type = None
    model = None

    def __init__(self, params):
        self.extract_sort(params)
        self.extract_pagination(params)
        q = params.pop('q', '')

        params = self.clean_parameters(params)

        super(SearchQuery, self).__init__(q, params)

    def clean_parameters(self, params):
        '''Only keep known parameters'''
        return {k: v for k, v in params.items() if k in self.adapter.facets}

    def extract_sort(self, params):
        '''Extract and build sort query from parameters'''
        sorts = params.pop('sort', [])
        sorts = [sorts] if isinstance(sorts, str) else sorts
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
            if isinstance(agg, Bucket):
                search.aggs.bucket(f, agg)
            elif isinstance(agg, Pipeline):
                search.aggs.pipeline(f, agg)
            else:
                search.aggs.metric(f, agg)

    def filter(self, search):
        '''
        Perform filtering instead of default post-filtering.
        '''
        if not self._filters:
            return search
        for f in self._filters.values():
            search = search.query(f)  # this will make a Bool(must=filter)
        return search

    def search(self):
        """
        Construct the Search object.
        """
        s = Search(doc_type=self.doc_types, using=es.client,
                   index=es.index_name)
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
        '''
        Customize the search query if necessary.

        It handles the following features:
         - negation support
         - optional fuzziness
         - optional analyzer
         - optional match_type
        '''
        if not query:
            return search

        included, excluded = [], []
        for term in query.split(' '):
            if not term.strip():
                continue
            if term.startswith('-'):
                excluded.append(term[1:])
            else:
                included.append(term)
        if included:
            search = search.query(self.multi_match(included))
        for term in excluded:
            search = search.query(~self.multi_match([term]))
        return search

    def build_search(self):
        s = super(SearchQuery, self).build_search()
        # Handle scoring functions
        if self.boosters:
            s.query = FunctionScore(query=s.query, functions=[
                b.to_query() for b in self.boosters
            ])
        # Until https://github.com/elastic/elasticsearch-dsl-py/pull/474
        # is merged and released
        s = s.fields([])
        return s

    def multi_match(self, terms):
        params = {'query': ' '.join(terms)}
        if len(terms) > 1:
            params['operator'] = 'and'
        # Optional search type
        if self.match_type:
            params['type'] = self.match_type
        # Optional analyzer
        if self.analyzer:
            params['analyzer'] = self.analyzer
        # Optional fuzzines
        if self.fuzzy:
            params['fuzziness'] = 'AUTO'
            params['prefix_length'] = 2  # Make it configurable ?
        return Q('multi_match', fields=self.fields, **params)

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
