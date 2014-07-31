# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import date, datetime, timedelta

from bson.objectid import ObjectId

from udata.models import db


log = logging.getLogger(__name__)

__all__ = ('Sort',
    'BoolFacet', 'TermFacet', 'ModelTermFacet',
    'RangeFacet', 'DateRangeFacet', 'TemporalCoverageFacet',
    'BoolBooster', 'FunctionBooster',
    'GaussDecay', 'ExpDecay', 'LinearDecay',
)


ES_NUM_FAILURES = '-Infinity', 'Infinity', 'NaN'


class Sort(object):
    def __init__(self, field):
        self.field = field


class Facet(object):
    def __init__(self, field, label=None, filter_label=None, icon=None):
        self.field = field

    def to_query(self, **kwargs):
        '''Get the elasticsearch facet query'''
        raise NotImplementedError

    def to_filter(self, value):
        '''Extract the elasticsearch query from the kwarg value filter'''
        raise NotImplementedError

    def from_response(self, name, response):
        '''Parse the elasticsearch response'''
        raise NotImplementedError

    def labelize(self, value):
        '''Get the label for a given value'''
        return value

    def to_aggregations(self):
        return {}


class BoolFacet(Facet):
    def to_query(self, **kwargs):
        query = {
            'terms': {
                'field': self.field,
                'size': 2,
            }
        }
        return query

    def to_filter(self, value):
        boolean = value is True or (isinstance(value, basestring) and value.lower() == 'true')
        return {'term': {self.field: boolean}}

    def from_response(self, name, response):
        facet = response.get('facets', {}).get(name)
        if not facet:
            return
        data = {
            'type': 'bool',
            'visible': len(facet['terms']) == 2,
        }
        for row in facet['terms']:
            data[row['term']] = row['count']
        return data


class TermFacet(Facet):
    def to_query(self, size=10, args=None, **kwargs):
        query = {
            'terms': {
                'field': self.field,
                'size': size,
            }
        }
        if args:
            query['terms']['exclude'] = [args] if isinstance(args, basestring) else args
        return query

    def to_filter(self, value):
        if isinstance(value, (list, tuple)):
            return [{'term': {self.field: v}} for v in value]
        else:
            return {'term': {self.field: value}}

    def from_response(self, name, response):
        facet = response.get('facets', {}).get(name)
        if not facet:
            return
        return {
            'type': 'terms',
            'terms': [(r['term'], r['count']) for r in facet['terms']],
            'visible': len(facet['terms']) > 0,
        }


class ModelTermFacet(TermFacet):
    def __init__(self, field, model):
        super(ModelTermFacet, self).__init__(field)
        self.model = model

    def from_response(self, name, response):
        is_objectid = isinstance(self.model.id, db.ObjectIdField)
        cast = lambda o: ObjectId(o) if is_objectid else o

        facet = response.get('facets', {}).get(name)
        if not facet:
            return
        ids = [term['term'] for term in facet['terms']]
        if is_objectid:
            ids = map(ObjectId, ids)

        objects = self.model.objects.in_bulk(ids)

        return {
            'type': 'models',
            'models': [
                (objects.get(cast(f['term'])), f['count'])
                for f in facet['terms']
            ],
            'visible': len(facet['terms']) > 0,
        }

    def labelize(self, value):
        return unicode(self.model.objects.get(id=value))


class RangeFacet(Facet):
    def __init__(self, field, cast=int):
        super(RangeFacet, self).__init__(field)
        self.cast = cast

    def to_query(self, **kwargs):
        return {
            'statistical': {
                'field': self.field
            }
        }

    def to_filter(self, value):
        boundaries = [self.cast(v) for v in value.split('-')]
        return {
            'range': {
                self.field: {
                    'gte': min(*boundaries),
                    'lte': max(*boundaries),
                }
            }
        }

    def from_response(self, name, response):
        facet = response.get('facets', {}).get(name)
        if not facet:
            return
        failure = facet['min'] in ES_NUM_FAILURES or facet['max'] in ES_NUM_FAILURES
        return {
            'type': 'range',
            'min': None if failure else self.cast(facet['min']),
            'max': None if failure else self.cast(facet['max']),
            'visible': not failure and facet['max'] - facet['min'] > 2,
        }


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
                self.field: {
                    'lte': max(date1, date2).isoformat(),
                    'gte': min(date1, date2).isoformat(),
                },
            }
        }

    def from_response(self, name, response):
        facet = response.get('facets', {}).get(name)
        if not facet:
            return
        min_value = ts_to_dt(facet['min'])
        max_value = ts_to_dt(facet['max'])
        return {
            'type': 'daterange',
            'min': min_value,
            'max': max_value,
            'visible': (max_value - min_value) > timedelta(days=2),
        }


class TemporalCoverageFacet(Facet):
    def to_query(self, **kwargs):
        '''No facet query, only use aggregation'''
        return None

    def _from_iso(self, value):
        parts = value.split('-') if isinstance(value, basestring) else value
        return date(*map(int, parts[0:3]))

    def to_filter(self, value):
        parts = value.split('-')
        date1 = date(*map(int, parts[0:3]))
        date2 = date(*map(int, parts[3:6]))
        return [{
            'range': {
                '{0}.start'.format(self.field): {
                    'lte': max(date1, date2).toordinal(),
                },
            }
        }, {
            'range': {
                '{0}.end'.format(self.field): {
                    'gte': min(date1, date2).toordinal(),
                },
            }
        }]

    def from_response(self, name, response):
        aggregations = response.get('aggregations', {})
        min_value = aggregations.get('{0}_min'.format(self.field), {}).get('value')
        max_value = aggregations.get('{0}_max'.format(self.field), {}).get('value')

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

    def to_aggregations(self):
        return {
            '{0}_min'.format(self.field): {
                'min': {
                    'field': '{0}.start'.format(self.field)
                }
            },
            '{0}_max'.format(self.field): {
                'max': {
                    'field': '{0}.end'.format(self.field)
                }
            }
        }


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
