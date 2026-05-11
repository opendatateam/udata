import copy
import json
import logging
import urllib.parse

from elasticsearch.exceptions import BadRequestError
from flask import abort, current_app, request

from udata.search.result import SearchResult

DEFAULT_PAGE_SIZE = 20
# Elasticsearch default max_result_window is 10000
ES_MAX_RESULT_WINDOW = 10000
DEFAULT_MAX_FACET_SIZE = 500
log = logging.getLogger(__name__)


def parse_facet_size(key, raw, max_facet_size):
    try:
        value = int(raw)
    except (ValueError, TypeError):
        abort(400, f"Invalid value for {key}: {raw!r} is not an integer.")
    if value < 1:
        abort(400, f"Invalid value for {key}: must be at least 1.")
    if value > max_facet_size:
        abort(400, f"Invalid value for {key}: must be at most {max_facet_size}.")
    return value


class SearchQuery:
    adapter = None
    model = None

    def __init__(self, params):
        self.page = max(1, int(params.pop("page", 1)))
        self.page_size = max(1, int(params.pop("page_size", DEFAULT_PAGE_SIZE)))
        offset = (self.page - 1) * self.page_size + self.page_size
        if offset > ES_MAX_RESULT_WINDOW:
            max_page = ES_MAX_RESULT_WINDOW // self.page_size
            abort(
                400,
                f"Result window is too large: page {self.page} with page_size {self.page_size} "
                f"exceeds the maximum of {ES_MAX_RESULT_WINDOW} results. "
                f"Maximum page for this page_size is {max_page}.",
            )
        self._query = params.pop("q", "")
        self.sort = params.pop("sort", None)
        max_facet_size = current_app.config.get("MAX_FACET_SIZE", DEFAULT_MAX_FACET_SIZE)
        self._facet_sizes = {}
        for key in [k for k in list(params.keys()) if k.startswith("facet_size__")]:
            facet_name = key[len("facet_size__") :]
            self._facet_sizes[facet_name] = parse_facet_size(key, params.pop(key), max_facet_size)
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
        if current_app.config["ELASTICSEARCH_URL"]:
            from udata.search import get_elastic_client

            service = self.adapter.service_class(get_elastic_client())
            try:
                results, total, total_pages, facets = service.search(self.to_search_params())
            except BadRequestError as e:
                log.error(
                    "Elasticsearch BadRequestError for %s: %s",
                    self.adapter.__name__,
                    json.dumps(e.body, indent=2, default=str),
                )
                raise
            result_dicts = [{"id": r.id} for r in results]
            return SearchResult(
                query=self,
                result=result_dicts,
                page=self.page,
                page_size=self.page_size,
                total=total,
                facets=facets,
            )
        else:
            params = self.to_search_params()
            result = self.adapter.mongo_search(params)
            return SearchResult(
                query=self, mongo_objects=list(result), total=result.total, **params
            )

    def to_search_params(self):
        params = {
            "q": self._query,
            "page": self.page,
            "page_size": self.page_size,
            "sort": self.sort,
            "facet_sizes": self._facet_sizes,
        }
        params.update(self._filters)
        return params

    # FIXME: unused?
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
