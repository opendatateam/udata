import copy
import logging
import requests

from flask import request
from werkzeug.urls import Href

from udata.search.result import SearchResult

DEFAULT_PAGE_SIZE = 20
log = logging.getLogger(__name__)


class SearchQuery:
    adapter = None
    model = None

    def __init__(self, params):
        self.extract_sort(params)
        self.page = int(params.pop('page', 1))
        self.page_size = int(params.pop('page_size', DEFAULT_PAGE_SIZE))
        self._query = params.pop('q', '')

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

    def exsearch(self):
        r = requests.get(f'{self.adapter.search_url}?q={self._query}&page={self.page}&page_size={self.page_size}').json()
        results = self.adapter.serialize_results(r.pop('data'))
        return SearchResult(query=self, result=results, **r)

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
