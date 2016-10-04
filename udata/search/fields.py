# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import date, datetime, timedelta

from bson.objectid import ObjectId

from udata.models import db
from udata.i18n import lazy_gettext as _, format_date
from udata.utils import to_bool

from elasticsearch_dsl import A
from elasticsearch_dsl.faceted_search import (
    TermsFacet as DSLTermsFacet, RangeFacet as DSLRangeFacet
)


log = logging.getLogger(__name__)

__all__ = (
    'Sort',
    'TermsFacet', 'ModelTermsFacet',
    'RangeFacet', 'DateRangeFacet', 'TemporalCoverageFacet',
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


def ts_to_dt(value):
    '''Convert an elasticsearch timestamp into a Python datetime'''
    return datetime.fromtimestamp(value * 1E-3)


class DateRangeFacet(RangeFacet):
    def to_filter(self, value):
        parts = value.split('-')
        date1 = date(*map(int, parts[0:3]))
        date2 = date(*map(int, parts[3:6]))
        return {
            'range': {
                self._params['field']: {
                    'lte': max(date1, date2).isoformat(),
                    'gte': min(date1, date2).isoformat(),
                },
            }
        }

    def from_response(self, name, response, fetch=True):
        aggregation = response.get('aggregations', {}).get(name)
        if not aggregation:
            return
        min_value = ts_to_dt(aggregation['min'])
        max_value = ts_to_dt(aggregation['max'])
        return {
            'type': 'daterange',
            'min': min_value,
            'max': max_value,
            'visible': (max_value - min_value) > timedelta(days=2),
        }


class TemporalCoverageFacet(Facet):
    def to_query(self):
        '''No direct query, only use aggregation via `to_aggregations`'''
        pass

    def parse_value(self, value):
        parts = value.split('-')
        start = date(*map(int, parts[0:3]))
        end = date(*map(int, parts[3:6]))
        return start, end

    def to_filter(self, value):
        start, end = self.parse_value(value)
        return [{
            'range': {
                '{0}.start'.format(self._params['field']): {
                    'lte': max(start, end).toordinal(),
                },
            }
        }, {
            'range': {
                '{0}.end'.format(self._params['field']): {
                    'gte': min(start, end).toordinal(),
                },
            }
        }]

    def from_response(self, name, response, fetch=True):
        aggregations = response.get('aggregations', {})
        min_value = aggregations.get(
            '{0}_min'.format(self._params['field']), {}).get('value')
        max_value = aggregations.get(
            '{0}_max'.format(self._params['field']), {}).get('value')

        if not (min_value and max_value):
            return None

        min_date = date.fromordinal(int(min_value))
        max_date = date.fromordinal(int(max_value))

        return {
            'type': 'temporal-coverage',
            'min': min_date,
            'max': max_date,
            'visible': (max_date - min_date) > timedelta(days=2),
        }

    def to_aggregations(self, name, *args):
        kwmin = {'field': '{0}.start'.format(self._params['field'])}
        kwmax = {'field': '{0}.end'.format(self._params['field'])}
        return {
            '{0}_min'.format(name): A('min', **kwmin),
            '{0}_max'.format(name): A('max', **kwmax),
        }

    def labelize(self, label, value):
        start, end = self.parse_value(value)
        return '{0}: {1} - {2}'.format(label, format_date(start, 'short'),
                                       format_date(end, 'short'))


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
