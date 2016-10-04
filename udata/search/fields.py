# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from bson.objectid import ObjectId

from udata.models import db

from elasticsearch_dsl import A
from elasticsearch_dsl.faceted_search import (
    TermsFacet as DSLTermsFacet, RangeFacet as DSLRangeFacet,
    DateHistogramFacet
)


log = logging.getLogger(__name__)

__all__ = (
    'Sort',
    'TermsFacet', 'ModelTermsFacet',
    'RangeFacet', 'DateHistogramFacet',
    'BoolBooster', 'FunctionBooster',
    'GaussDecay', 'ExpDecay', 'LinearDecay',
)


ES_NUM_FAILURES = '-Infinity', 'Infinity', 'NaN', None


class Sort(object):
    def __init__(self, field):
        self.field = field


class Facet(object):

    def __init__(self, **kwargs):
        super(Facet, self).__init__(**kwargs)
        self.labelize = self._params.pop('labelizer',
                                         lambda label, value: value)

    def filter_from_kwargs(self, name, kwargs):
        pass

    def to_aggregations(self, name, *args):
        pass


class TermsFacet(Facet, DSLTermsFacet):
    pass


class ModelTermsFacet(TermsFacet):
    def __init__(self, field, model, labelizer=None, field_name='id'):
        super(ModelTermsFacet, self).__init__(field=field, labelizer=labelizer)
        self.model = model
        self.field_name = field_name

    def get_values(self, data, filter_values):
        """
        Turn the raw bucket data into a list of tuples containing the object,
        number of documents and a flag indicating whether this value has been
        selected or not.
        """
        values = super(ModelTermsFacet, self).get_values(data, filter_values)
        ids = [key for (key, doc_count, selected) in values]
        # Perform a model resolution: models are feched from DB
        # Depending on used models, ID can be a String or an ObjectId
        is_objectid = isinstance(getattr(self.model, self.field_name),
                                 db.ObjectIdField)
        cast = ObjectId if is_objectid else lambda o: o
        if is_objectid:
            # Cast identifier as ObjectId if necessary
            # (in_bullk expect ObjectId and does not cast if necessary)
            ids = map(ObjectId, ids)
        objects = self.model.objects.in_bulk(ids)

        def serialize(term):
            return objects.get(cast(term))

        return [
            (serialize(key), doc_count)
            for (key, doc_count, selected) in values
        ]

    def labelize(self, label, value):
        return (self.labelizer(label, value)
                if self.labelizer
                else unicode(self.model.objects.get(id=value)))


class RangeFacet(Facet, DSLRangeFacet):

    def to_query(self, **kwargs):
        return {
            'stats': {
                'field': self._params['field']
            }
        }

    def to_aggregations(self, name, size=20, *args):
        return {name: A('stats', field=self._params['field'])}

    def to_filter(self, value):
        boundaries = [self.cast(v) for v in value.split('-')]
        return {
            'range': {
                self._params['field']: {
                    'gte': min(*boundaries),
                    'lte': max(*boundaries),
                }
            }
        }

    def from_response(self, name, response, fetch=True):
        aggregation = response.get('aggregations', {}).get(name)
        if not aggregation:
            return
        failure = (aggregation['min'] in ES_NUM_FAILURES or
                   aggregation['max'] in ES_NUM_FAILURES)
        return {
            'type': 'range',
            'min': None if failure else self.cast(aggregation['min']),
            'max': None if failure else self.cast(aggregation['max']),
            'visible': (not failure and
                        aggregation['max'] - aggregation['min'] > 2),
        }

    def labelize(self, label, value):
        return (self.labelizer(label, value)
                if self.labelizer else ': '.join([label, value]))


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


def _v(value):
    '''Call value if necessary'''
    return value() if callable(value) else value


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
            'origin': _v(self.origin),
            'scale': _v(self.scale),
        }
        if self.offset:
            params['offset'] = _v(self.offset)
        if self.decay:
            params['decay'] = _v(self.decay)

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
