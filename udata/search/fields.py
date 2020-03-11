import logging
import re

from datetime import date

from bson.objectid import ObjectId
from elasticsearch_dsl import Q, A
from elasticsearch_dsl.faceted_search import (
    Facet as DSLFacet,
    TermsFacet as DSLTermsFacet,
    RangeFacet as DSLRangeFacet,
)
from flask_restplus import inputs
from jinja2 import Markup
from speaklater import is_lazy_string

from udata.i18n import lazy_gettext as _, format_date
from udata.utils import to_bool, safe_unicode, clean_string

log = logging.getLogger(__name__)

__all__ = (
    'BoolFacet', 'TermsFacet', 'ModelTermsFacet',
    'RangeFacet', 'TemporalCoverageFacet',
    'BoolBooster', 'FunctionBooster', 'ValueFactor',
    'GaussDecay', 'ExpDecay', 'LinearDecay',
)


ES_NUM_FAILURES = '-Infinity', 'Infinity', 'NaN', None

RE_TIME_COVERAGE = re.compile(r'\d{4}-\d{2}-\d{2}-\d{4}-\d{2}-\d{2}')

OR_SEPARATOR = '|'
OR_LABEL = _('OR')


def obj_to_string(obj):
    '''Render an object into a unicode string if possible'''
    if not obj:
        return None
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')
    elif isinstance(obj, str):
        return obj
    elif is_lazy_string(obj):
        return obj.value
    elif hasattr(obj, '__html__'):
        return obj.__html__()
    else:
        return str(obj)


class Facet(object):
    def __init__(self, **kwargs):
        super(Facet, self).__init__(**kwargs)
        self.labelizer = self._params.pop('labelizer', None)

    def labelize(self, value):
        labelize = self.labelizer or self.default_labelizer
        if isinstance(value, str):
            labels = (labelize(v) for v in value.split(OR_SEPARATOR))
            labels = (obj_to_string(l) for l in labels)
            labels = (l for l in labels if l)
            or_label = str(' {0} '.format(OR_LABEL))
            return Markup(or_label.join(labels))
        return Markup(obj_to_string(labelize(value)))

    def default_labelizer(self, value):
        return clean_string(safe_unicode(value))

    def as_request_parser_kwargs(self):
        return {'type': clean_string}

    def validate_parameter(self, value):
        return value

    def get_value_filter(self, value):
        self.validate_parameter(value)  # Might trigger a double validation
        return super(Facet, self).get_value_filter(value)


class TermsFacet(Facet, DSLTermsFacet):
    def add_filter(self, filter_values):
        """Improve the original one to deal with OR cases."""
        field = self._params['field']
        # Build a `AND` query on values wihtout the OR operator.
        # and a `OR` query for each value containing the OR operator.
        filters = [
            Q('bool', should=[
                Q('term',  **{field: v}) for v in value.split(OR_SEPARATOR)
            ])
            if OR_SEPARATOR in value else
            Q('term',  **{field: value})
            for value in filter_values
        ]
        return Q('bool', must=filters) if len(filters) > 1 else filters[0]


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

    def default_labelizer(self, value):
        return str(_('yes') if to_bool(value) else _('no'))

    def as_request_parser_kwargs(self):
        return {'type': inputs.boolean}


class ModelTermsFacet(TermsFacet):
    def __init__(self, field, model, labelizer=None, field_name='id'):
        super(ModelTermsFacet, self).__init__(field=field, labelizer=labelizer)
        self.model = model
        self.field_name = field_name

    @property
    def model_field(self):
        return getattr(self.model, self.field_name)

    def get_values(self, data, filter_values):
        """
        Turn the raw bucket data into a list of tuples containing the object,
        number of documents and a flag indicating whether this value has been
        selected or not.
        """
        values = super(ModelTermsFacet, self).get_values(data, filter_values)
        ids = [key for (key, doc_count, selected) in values]
        # Perform a model resolution: models are feched from DB
        # We use model field to cast IDs
        ids = [self.model_field.to_mongo(id) for id in ids]
        objects = self.model.objects.in_bulk(ids)

        return [
            (objects.get(self.model_field.to_mongo(key)), doc_count, selected)
            for (key, doc_count, selected) in values
        ]

    def default_labelizer(self, value):
        if not isinstance(value, self.model):
            self.validate_parameter(value)
            id = self.model_field.to_mongo(value)
            value = self.model.objects.get(id=id)
        return safe_unicode(value)

    def validate_parameter(self, value):
        if isinstance(value, ObjectId):
            return value
        try:
            return [
                self.model_field.to_mongo(v)
                for v in value.split(OR_SEPARATOR)
            ]
        except Exception:
            raise ValueError('"{0}" is not valid identifier'.format(value))


class RangeFacet(Facet, DSLRangeFacet):
    '''
    A Range facet with splited keys and labels.

    This separation allows:
    - readable keys (without spaces and special chars) in URLs (front and API)
    - lazily localizable labels (without changing API by language)
    '''
    def __init__(self, **kwargs):
        super(RangeFacet, self).__init__(**kwargs)
        self.labels = self._params.pop('labels', {})
        if len(self.labels) != len(self._ranges):
            raise ValueError('Missing some labels')
        for key in self.labels.keys():
            if key not in self._ranges:
                raise ValueError('Unknown label key {0}'.format(key))

    def get_value_filter(self, filter_value):
        '''
        Fix here until upstream PR is merged
        https://github.com/elastic/elasticsearch-dsl-py/pull/473
        '''
        self.validate_parameter(filter_value)
        f, t = self._ranges[filter_value]
        limits = {}
        # lt and gte to ensure non-overlapping ranges
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

    def default_labelizer(self, value):
        self.validate_parameter(value)
        return self.labels.get(value, value)

    def as_request_parser_kwargs(self):
        return {'type': self.validate_parameter, 'choices': list(self.labels)}

    def validate_parameter(self, value):
        if value not in self.labels:
            raise ValueError('Unknown range key: {0}'.format(value))
        return value


def get_value(data, name):
    wrapper = getattr(data, name, {})
    return getattr(wrapper, 'value')


class TemporalCoverageFacet(Facet, DSLFacet):
    agg_type = 'nested'

    def parse_value(self, value):
        parts = value.split('-')
        start = date(*map(int, parts[0:3]))
        end = date(*map(int, parts[3:6]))
        return start, end

    def default_labelizer(self, value):
        self.validate_parameter(value)
        start, end = self.parse_value(value)
        return ' - '.join((format_date(start, 'short'),
                           format_date(end, 'short')))

    def get_aggregation(self):
        field = self._params['field']
        a = A('nested', path=field)
        a.metric('min_start', 'min', field='{0}.start'.format(field))
        a.metric('max_end', 'max', field='{0}.end'.format(field))
        return a

    def get_value_filter(self, value):
        self.validate_parameter(value)
        field = self._params['field']
        start, end = self.parse_value(value)
        range_start = Q({'range': {'{0}.start'.format(field): {
            'lte': max(start, end).toordinal(),
        }}})
        range_end = Q({'range': {'{0}.end'.format(field): {
            'gte': min(start, end).toordinal(),
        }}})
        return Q('nested', path=field, query=range_start & range_end)

    def get_values(self, data, filter_values):
        field = self._params['field']
        min_value = get_value(data, 'min_start'.format(field))
        max_value = get_value(data, 'max_end'.format(field))

        if not (min_value and max_value):
            return None

        return {
            'min': date.fromordinal(int(min_value)),
            'max': date.fromordinal(int(max_value)),
            'days': max_value - min_value,
        }

    def validate_parameter(self, value):
        if not isinstance(value, str) \
                or not RE_TIME_COVERAGE.match(value):
            msg = '"{0}" does not match YYYY-MM-DD-YYYY-MM-DD'.format(value)
            raise ValueError(msg)
        return value

    def as_request_parser_kwargs(self):
        return {
            'type': self.validate_parameter,
            'help': _('A date range expressed as start-end '
                      'where both dates are in iso format '
                      '(ie. YYYY-MM-DD-YYYY-MM-DD)')
        }


def _v(value):
    '''Call value if necessary'''
    return value() if callable(value) else value


class BoolBooster(object):
    def __init__(self, field, factor):
        self.field = field
        self.factor = factor

    def to_query(self):
        return {
            'filter': {'term': {self.field: True}},
            'boost_factor': _v(self.factor),
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


class ValueFactor(object):
    def __init__(self, field, **params):
        self.params = params
        self.params['field'] = field

    def to_query(self):
        return {'field_value_factor': self.params}


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
