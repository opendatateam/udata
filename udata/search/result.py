# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import logging

from bson.objectid import ObjectId
from flask import request
from werkzeug.urls import Href

from udata.utils import Paginable


log = logging.getLogger(__name__)


class SearchResult(Paginable):
    '''An ElasticSearch result wrapper for easy property access'''
    def __init__(self, query, result):
        self.result = result
        self.query = query
        self._objects = None

    @property
    def total(self):
        return self.result.hits.total

    @property
    def max_score(self):
        return self.result.hits.max_score

    @property
    def pages(self):
        return 1
        # return (self.query.page or 1) or 1

    @property
    def page_size(self):
        return self.query.page_size

    @property
    def class_name(self):
        return self.query.adapter.model.__name__

    def get_ids(self):
        from beeprint import pp
        pp(self.result)
        return [hit['_id'] for hit in self.result.hits.hits]

    def get_objects(self):
        if not self._objects:
            ids = [ObjectId(id) for id in self.get_ids()]
            objects = self.query.model.objects.in_bulk(ids)
            self._objects = [objects.get(id) for id in ids]
        return self._objects

    @property
    def objects(self):
        return self.get_objects()

    @property
    def facets(self):
        return self.result.facets.to_dict()

    def __iter__(self):
        for obj in self.get_objects():
            yield obj

    def __len__(self):
        return len(self.result.hits.hits)

    def __getitem__(self, index):
        return self.get_objects()[index]

    def get_aggregation(self, name, fetch=True):
        pass  # TODO: remove

    def get_range(self, name):
        min_name = '{0}_min'.format(name)
        max_name = '{0}_max'.format(name)
        if name not in self.query.adapter.filters:
            return None
        aggregations = self.result.get('aggregations', {})
        if (not aggregations
                or min_name not in aggregations
                or max_name not in aggregations):
            return None
        spec = self.query.adapter.filters[name]
        min_value = aggregations[min_name]['value'] or 0
        max_value = aggregations[max_name]['value'] or 0
        return {
            'min': spec.cast(min_value),
            'max': spec.cast(max_value),
            'query_min': 0,
            'query_max': 0,
        }

    def label_func(self, name):
        if name not in self.query.facets:
            return None
        return self.query.facets[name].labelize

    def labelize(self, name, value):
        func = self.label_func(name)
        return func(value) if func else value

    def to_url(self, url=None, replace=False, **kwargs):
        '''Serialize the query into an URL'''
        params = copy.deepcopy(self.query._filters)
        params['q'] = self.query._query
        if kwargs:
            params.pop('page', None)
            for key, value in kwargs.items():
                if not replace and key in params:
                    if not isinstance(params[key], (list, tuple)):
                        params[key] = [params[key], value]
                    else:
                        params[key].append(value)
                else:
                    params[key] = value
        params.pop('facets', None)  # Always true when used
        href = Href(url or request.base_url)
        return href(params)


class SearchIterator(object):
    """An ElasticSearch scroll result iterator

    that fetch objects on each hit.
    """
    def __init__(self, query, result):
        self.result = result or self._empty()
        self.query = query

    def _empty(self):
        return (x for x in list())

    def __iter__(self):
        for hit in self.result:
            yield self.query.adapter.model.objects.get(id=hit['_id'])
