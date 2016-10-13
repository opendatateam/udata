# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import logging

from bson.objectid import ObjectId
from flask import request
from werkzeug.urls import Href

from elasticsearch_dsl.result import Response

from udata.utils import Paginable


log = logging.getLogger(__name__)


class SearchResult(Paginable, Response):
    '''An ElasticSearch result wrapper for easy property access'''
    def __init__(self, query, result, *args, **kwargs):
        super(SearchResult, self).__init__(result, *args, **kwargs)
        self.query = query
        self._objects = None
        self._facets = None

    @property
    def query_string(self):
        return self.query._query

    @property
    def facets(self):
        if self._facets is None:
            self._facets = {}
            for name, facet in self.query.facets.items():
                self._facets[name] = facet.get_values(
                    self.aggregations[name]['buckets'],
                    self.query.filter_values.get(name, ())
                )
        return self._facets

    @property
    def total(self):
        try:
            return self.hits.total
        except (KeyError, AttributeError):
            return 0

    @property
    def max_score(self):
        try:
            return self.hits.max_score
        except (KeyError, AttributeError):
            return 0

    @property
    def page(self):
        return (self.query.page or 1) if self.pages else 1

    @property
    def page_size(self):
        return self.query.page_size

    @property
    def class_name(self):
        return self.query.adapter.model.__name__

    def get_ids(self):
        try:
            return [hit['_id'] for hit in self.hits.hits]
        except KeyError:
            return []

    def get_objects(self):
        if not self._objects:
            ids = [ObjectId(id) for id in self.get_ids()]
            objects = self.query.model.objects.in_bulk(ids)
            self._objects = [objects.get(id) for id in ids]
        return self._objects

    @property
    def objects(self):
        return self.get_objects()

    def __iter__(self):
        for obj in self.get_objects():
            yield obj

    def __len__(self):
        return len(self.hits.hits)

    def __getitem__(self, index):
        return self.get_objects()[index]

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
