# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from bson.objectid import ObjectId

from udata.utils import Paginable


log = logging.getLogger(__name__)


class SearchResult(Paginable):
    '''An ElasticSearch result wrapper for easy property access'''
    def __init__(self, query, result):
        self.result = result
        self.query = query

    @property
    def total(self):
        return self.result.get('hits', {}).get('total', 0)

    @property
    def max_score(self):
        return self.result.get('hits', {}).get('max_score', 0)

    @property
    def page(self):
        return self.query.page

    @property
    def page_size(self):
        return self.query.page_size

    def get_ids(self):
        return [hit['_id'] for hit in self.result.get('hits', {}).get('hits', [])]

    def get_objects(self):
        ids = [ObjectId(id) for id in self.get_ids()]
        objects = self.query.adapter.model.objects.in_bulk(ids)
        return [objects.get(id) for id in ids]

    def __iter__(self):
        for obj in self.get_objects():
            yield obj

    def __len__(self):
        return len(self.result.get('hits', {}).get('hits', []))

    def __getitem__(self, index):
        return self.get_objects()[index]

    def get_facet(self, name):
        if not name in self.query.adapter.facets:
            return None
        return self.query.adapter.facets[name].from_response(name, self.result)

    def get_range(self, name):
        min_name = '{0}_min'.format(name)
        max_name = '{0}_max'.format(name)
        if not name in self.query.adapter.filters:
            return None
        aggs = self.result.get('aggregations', {})
        if not aggs or not min_name in aggs or not max_name in aggs:
            return None
        spec = self.query.adapter.filters[name]
        min_value = aggs[min_name]['value'] or 0
        max_value = aggs[max_name]['value'] or 0
        return {
            'min': spec.cast(min_value),
            'max': spec.cast(max_value),
            'query_min': 0,
            'query_max': 0,
        }

    def label_func(self, name):
        if not name in self.query.adapter.facets:
            return None
        return self.query.adapter.facets[name].labelize

    def labelize(self, name, value):
        func = self.label_func(name)
        return func(value) if func else value
