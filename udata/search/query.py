import copy
import logging
import urllib.parse

import requests
from flask import current_app, request

from udata.search.result import SearchResult

DEFAULT_PAGE_SIZE = 20
log = logging.getLogger(__name__)


class SearchQuery:
    adapter = None
    model = None

    def __init__(self, params):
        self.page = int(params.pop("page", 1))
        self.page_size = int(params.pop("page_size", DEFAULT_PAGE_SIZE))
        self._query = params.pop("q", "")
        self.sort = params.pop("sort", None)
        self._filters = {}
        self.extract_filters(params)

    def extract_filters(self, params):
        for key, value in params.items():
            if key in self._filters:
                if not isinstance(self._filters[key], (list, tuple)):
                    self._filters[key] = [self._filters[key], value]
                else:
                    self._filters[key].append(value)
            else:
                self._filters[key] = value

    def execute_search(self):
        # If SEARCH_SERVICE_API_URL is set, the remote search service will be queried.
        # Otherwise mongo search will be used instead.
        if current_app.config["SEARCH_SERVICE_API_URL"]:
            url = f"{current_app.config['SEARCH_SERVICE_API_URL']}{self.adapter.search_url}?q={self._query}&page={self.page}&page_size={self.page_size}"
            if self.sort:
                url = url + f"&sort={self.sort}"
            for name, value in self._filters.items():
                url = url + f"&{name}={value}"
            r = requests.get(url, timeout=current_app.config["SEARCH_SERVICE_REQUEST_TIMEOUT"])
            r.raise_for_status()
            result = r.json()
            return SearchResult(query=self, result=result.pop("data"), **result)
        else:
            query_args = {
                "q": self._query,
                "page": self.page,
                "page_size": self.page_size,
                "sort": self.sort,
            }
            query_args.update(self._filters)
            result = self.adapter.mongo_search(query_args)
            return SearchResult(
                query=self, mongo_objects=list(result), total=result.total, **query_args
            )

    def to_url(self, url=None, replace=False, **kwargs):
        """Serialize the query into an URL"""
        params = copy.deepcopy(self._filters)
        if self._query:
            params["q"] = self._query
        if self.page_size != DEFAULT_PAGE_SIZE:
            params["page_size"] = self.page_size
        if self.sort:
            params["sort"] = self.sort
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
            params["page"] = self.page
        return f"{url or request.base_url}?{urllib.parse.urlencode(params)}"
