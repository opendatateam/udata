import logging
import re

from bson.objectid import ObjectId
from webargs import ValidationError

log = logging.getLogger(__name__)

__all__ = (
    'model_filter_validation', 'temporal_coverage_filter_validation'
)


ES_NUM_FAILURES = '-Infinity', 'Infinity', 'NaN', None

RE_TIME_COVERAGE = re.compile(r'\d{4}-\d{2}-\d{2}-\d{4}-\d{2}-\d{2}')

OR_SEPARATOR = '|'


def model_filter_validation(val, model, field_name='id'):
    if isinstance(val, ObjectId):
        return val
    try:
        return [
            getattr(model, field_name).to_mongo(v)
            for v in val.split(OR_SEPARATOR)
        ]
    except Exception:
        raise ValidationError('"{0}" is not valid identifier'.format(val))


def temporal_coverage_filter_validation(val):
    if not isinstance(val, str) \
            or not RE_TIME_COVERAGE.match(val):
        msg = '"{0}" does not match YYYY-MM-DD-YYYY-MM-DD'.format(val)
        raise ValidationError(msg)
    return val
