# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import time
from datetime import date

from bson.objectid import ObjectId

from udata.models import db


log = logging.getLogger(__name__)

__all__ = ('Sort',
    'RangeFilter', 'DateRangeFilter', 'BoolFilter',
    'TermFacet', 'ModelTermFacet', 'RangeFacet',
    'BoolBooster', 'FunctionBooster',
    'GaussDecay', 'ExpDecay', 'LinearDecay',
)


class Sort(object):
    def __init__(self, field):
        self.field = field


class RangeFilter(object):
    def __init__(self, field, cast=int):
        self.field = field
        self.cast = cast

    def to_query(self, value):
        start, end = value.split('-')
        return {self.field: {
            'gte': self.cast(start),
            'lte': self.cast(end),
        }}


class DateRangeFilter(object):
    def __init__(self, start_field, end_field):
        self.start_field = start_field
        self.end_field = end_field

    def to_query(self, value):
        parts = value.split('-')
        start = date(*map(int, parts[0:3]))
        end = date(*map(int, parts[3:6]))
        return {
            self.start_field: {'lte': end.isoformat()},
            self.end_field: {'gte': start.isoformat()},
        }

    def cast(self, value):
        t = time.gmtime(value)
        return date(t.tm_year, t.tm_mon, t.tm_mday)
        # return datetime.fromtimestamp(long(value)).date()


class BoolFilter(object):
    def __init__(self, field):
        self.field = field

    def to_query(self, value):
        return {
            'term': {self.field: value},
        }


class TermFacet(object):
    def __init__(self, field):
        self.field = field

    def to_query(self, size=10):
        return {
            'terms': {
                'field': self.field,
                'size': size,
            }
        }

    def get_values(self, facet, actives=None):
        actives = [actives] if isinstance(actives, basestring) else actives or []
        return [
            (term['term'], term['count'], term['term'] in actives)
            for term in facet['terms']
        ]


class ModelTermFacet(TermFacet):
    def __init__(self, field, model):
        super(ModelTermFacet, self).__init__(field)
        self.model = model

    def get_values(self, facet, actives=None):
        actives = [actives] if isinstance(actives, basestring) else actives or []
        ids = [term['term'] for term in facet['terms']]
        counts = [term['count'] for term in facet['terms']]
        if isinstance(self.model.id, db.ObjectIdField):
            ids = map(ObjectId, ids)
        objects = self.model.objects.in_bulk(ids)
        return [(objects.get(id), count, str(id) in actives) for id, count in zip(ids, counts)]


class RangeFacet(object):
    def __init__(self, field, ranges):
        self.field = field
        self.ranges = ranges

    def to_query(self):
        return {
            'range': {
                'field': self.field,
                'ranges': self.ranges,
            }
        }

    def get_values(self, facet, actives=None):
        actives = [actives] if isinstance(actives, basestring) else actives or []
        values = []
        for idx, r in enumerate(facet['ranges']):
            spec = self.ranges[idx]
            interval = '-'.join([str(spec.get('from', '')), str(spec.get('to', ''))])
            values.append((spec, r['count'], interval in actives))
        return values


class BoolBooster(object):
    def __init__(self, field, factor):
        self.field = field
        self.factor = factor

    def to_query(self):
        return {
            'filter': {'term': {self.field: True}},
            'boost_factor': self.factor,
        }


class FunctionBooster(object):
    def __init__(self, function):
        self.function = function

    def to_query(self):
        return {
            'script_score': {
                'script': self.function,
            },
        }


class DecayFunction(object):
    function = None

    def __init__(self, field, origin, scale=None, offset=None, decay=None):
        self.field = field
        self.origin = origin
        self.scale = scale or origin
        self.offset = offset
        self.decay = decay

    def to_query(self):
        params = {
            'origin': self.origin,
            'scale': self.scale,
        }
        if self.offset:
            params['offset'] = self.offset
        if self.decay:
            params['decay'] = self.decay

        return {
            self.function: {
                self.field: params
            },
        }


class GaussDecay(DecayFunction):
    function = 'gauss'


class ExpDecay(DecayFunction):
    function = 'exp'


class LinearDecay(DecayFunction):
    function = 'linear'
