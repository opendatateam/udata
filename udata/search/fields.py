# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from bson.objectid import ObjectId
from elasticsearch_dsl import Q
from elasticsearch_dsl.faceted_search import (
    Facet as DSLFacet,
    TermsFacet as DSLTermsFacet,
    RangeFacet as DSLRangeFacet,
    DateHistogramFacet as DSLDateHistogramFacet,
)

from udata.i18n import lazy_gettext as _
from udata.models import db
from udata.utils import to_bool

log = logging.getLogger(__name__)

__all__ = (
    'BoolFacet', 'TermsFacet', 'ModelTermsFacet',
    'RangeFacet', 'DateHistogramFacet',
    'BoolBooster', 'FunctionBooster',
    'GaussDecay', 'ExpDecay', 'LinearDecay',
)


ES_NUM_FAILURES = '-Infinity', 'Infinity', 'NaN', None


class Facet(object):

    def __init__(self, **kwargs):
        super(Facet, self).__init__(**kwargs)
        self.labelizer = self._params.pop('labelizer', None)

    def labelize(self, label, value):
        '''Get the label for a given value'''
        labelizer = self.labelizer or self.default_labelizer
        return labelizer(label, value)

    def default_labelizer(self, label, value):
        return str(value)


class TermsFacet(Facet, DSLTermsFacet):
    pass


class BoolFacet(Facet, DSLFacet):
    agg_type = 'terms'

    def get_values(self, data, filter_values):
        return [
            (to_bool(key), doc_count, selected)
            for (key, doc_count, selected)
            in super(BoolFacet, self).get_values(data, filter_values)
        ]

    def get_value_filter(self, filter_value):
        boolean = to_bool(filter_value)
        q = Q('term', **{self._params['field']: True})
        return q if boolean else ~q

    def default_labelizer(self, label, value):
        return str(_('yes') if to_bool(value) else _('no'))


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
            (serialize(key), doc_count, selected)
            for (key, doc_count, selected) in values
        ]

    def labelize(self, label, value):
        if not isinstance(value, self.model):
            value = self.model.objects.get(id=value)
        return super(ModelTermsFacet, self).labelize(label, value)


class RangeFacet(Facet, DSLRangeFacet):
    def __init__(self, **kwargs):
        super(RangeFacet, self).__init__(**kwargs)
        self.labels = self._params.pop('labels', {})

    def get_value_filter(self, filter_value):
        '''
        Fix here until upstream PR is merged
        https://github.com/elastic/elasticsearch-dsl-py/pull/473
        '''
        f, t = self._ranges[filter_value]
        limits = {}
        if f is not None:
            limits['gte'] = f
        if t is not None:
            limits['lt'] = t

        return Q('range', **{
            self._params['field']: limits
        })

    def get_values(self, data, filter_values):
        return [
            (key, count, selected)
            for key, count, selected
            in super(RangeFacet, self).get_values(data, filter_values)
            if count
        ]

    def default_labelizer(self, label, value):
        return self.labels.get(value, value)


class DateHistogramFacet(Facet, DSLDateHistogramFacet):
    pass


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
