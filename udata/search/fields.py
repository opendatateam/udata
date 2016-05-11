# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import date, datetime, timedelta

from bson.objectid import ObjectId

from udata.models import db
from udata.i18n import lazy_gettext as _, format_date
from udata.utils import to_bool


log = logging.getLogger(__name__)

__all__ = (
    'Sort',
    'BoolFacet', 'TermFacet', 'ModelTermFacet', 'ExtrasFacet',
    'RangeFacet', 'DateRangeFacet', 'TemporalCoverageFacet',
    'BoolBooster', 'FunctionBooster',
    'GaussDecay', 'ExpDecay', 'LinearDecay',
)


ES_NUM_FAILURES = '-Infinity', 'Infinity', 'NaN', None


class Sort(object):
    def __init__(self, field):
        self.field = field


class Facet(object):
    def __init__(self, field, labelizer=None):
        self.field = field
        self.labelizer = labelizer

    def to_query(self, **kwargs):
        '''Get the elasticsearch facet query'''
        raise NotImplementedError

    def to_filter(self, value):
        '''Extract the elasticsearch query from the kwarg value filter'''
        raise NotImplementedError

    def filter_from_kwargs(self, name, kwargs):
        if name in kwargs:
            value = kwargs[name]
            query = self.to_filter(value)
            if not query:
                return
            return {'must': ([query] if isinstance(query, dict) else query)}

    def from_response(self, name, response, fetch=True):
        '''
        Parse the elasticsearch response.
        :param bool fetch: whether to fetch the object from DB or not
        '''
        raise NotImplementedError

    def labelize(self, label, value):
        '''Get the label for a given value'''
        return self.labelizer(label, value) if self.labelizer else value

    def to_aggregations(self, name, *args):
        query = self.to_query(args=args)
        if query:
            return {name: query}
        else:
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

    def filter_from_kwargs(self, name, kwargs):
        if name not in kwargs:
            return
        value = kwargs[name]
        boolean = to_bool(value)
        if boolean:
            return {'must': [{'term': {self.field: True}}]}
        else:
            return {'must_not': [{'term': {self.field: True}}]}

    def from_response(self, name, response, fetch=True):
        aggregation = response.get('aggregations', {}).get(name)
        if not aggregation or not len(aggregation['terms']):
            return
        true_count = 0
        false_count = 0
        for row in aggregation['terms']:
            if row['term'] == 'T':
                true_count = row['count']
            else:
                false_count = row['count']
        false_count += aggregation['missing'] + aggregation['other']
        data = {
            'type': 'bool',
            'visible': true_count > 0 and false_count > 0,
            True: true_count,
            False: false_count
        }
        return data

    def labelize(self, label, value):
        return ': '.join([label,
                          unicode(_('yes') if to_bool(value) else _('no'))])


class TermFacet(Facet):
    def to_query(self, size=20, args=None, **kwargs):
        query = {
            'terms': {
                'field': self.field,
                'size': size,
            }
        }
        if args:
            query['terms']['exclude'] = (
                [args] if isinstance(args, basestring) else args)
        return query

    def to_filter(self, value):
        if isinstance(value, (list, tuple)):
            return [{'term': {self.field: v}} for v in value]
        else:
            return {'term': {self.field: value}}

    def from_response(self, name, response, fetch=True):
        aggregation = response.get('aggregations', {}).get(name)
        if not aggregation:
            return
        return {
            'type': 'terms',
            'terms': [(bucket['key'], bucket['doc_count'])
                      for bucket in aggregation['buckets']],
            'visible': len(aggregation['buckets']) > 1,
        }


class ModelTermFacet(TermFacet):
    def __init__(self, field, model, labelizer=None, field_name='id'):
        super(ModelTermFacet, self).__init__(field, labelizer)
        self.model = model
        self.field_name = field_name

    def from_response(self, name, response, fetch=True):
        aggregation = response.get('aggregations', {}).get(name)
        if not aggregation:
            return
        ids = [bucket['key'] for bucket in aggregation['buckets']]

        if fetch:
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
        else:
            # Only return the model class and its identifier
            def serialize(term):
                return {'class': self.model.__name__, 'id': term}

        return {
            'type': 'models',
            'models': [
                (serialize(bucket['key']), bucket['doc_count'])
                for bucket in aggregation['buckets']
            ],
            'visible': len(aggregation['buckets']) > 1,
        }

    def labelize(self, label, value):
        return (self.labelizer(label, value)
                if self.labelizer
                else unicode(self.model.objects.get(id=value)))


class ExtrasFacet(Facet):
    def to_query(self, **kwargs):
        pass

    def filter_from_kwargs(self, name, kwargs):
        prefix = '{0}.'.format(name)
        filters = []
        for key, value in kwargs.items():
            if key.startswith(prefix):
                filters.append({
                    'term': {key.replace(name, self.field): value}})
        return {'must': filters}

    def from_response(self, name, response, fetch=True):
        pass


class RangeFacet(Facet):
    def __init__(self, field, cast=int, labelizer=None):
        super(RangeFacet, self).__init__(field, labelizer)
        self.cast = cast

    def to_query(self, **kwargs):
        return {
            'stats': {
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
                self.field: {
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
                '{0}.start'.format(self.field): {
                    'lte': max(start, end).toordinal(),
                },
            }
        }, {
            'range': {
                '{0}.end'.format(self.field): {
                    'gte': min(start, end).toordinal(),
                },
            }
        }]

    def from_response(self, name, response, fetch=True):
        aggregations = response.get('aggregations', {})
        min_value = aggregations.get(
            '{0}_min'.format(self.field), {}).get('value')
        max_value = aggregations.get(
            '{0}_max'.format(self.field), {}).get('value')

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
        return {
            '{0}_min'.format(name): {
                'min': {
                    'field': '{0}.start'.format(self.field)
                }
            },
            '{0}_max'.format(name): {
                'max': {
                    'field': '{0}.end'.format(self.field)
                }
            }
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
