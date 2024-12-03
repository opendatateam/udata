import logging
import re

from bson.objectid import ObjectId
from flask_restx import inputs

from udata.utils import clean_string

log = logging.getLogger(__name__)

__all__ = ("BoolFilter", "ModelTermsFilter", "TemporalCoverageFilter", "Filter", "ListFilter")


ES_NUM_FAILURES = "-Infinity", "Infinity", "NaN", None

RE_TIME_COVERAGE = re.compile(r"\d{4}-\d{2}-\d{2}-\d{4}-\d{2}-\d{2}")

OR_SEPARATOR = "|"


class Filter:
    def __init__(self, choices=None):
        self.choices = choices

    def as_request_parser_kwargs(self):
        if self.choices:
            return {"type": clean_string, "choices": self.choices}
        return {"type": clean_string}


class ListFilter:
    @classmethod
    def as_request_parser_kwargs(self):
        return {"action": "append"}


class BoolFilter(Filter):
    @staticmethod
    def as_request_parser_kwargs():
        return {"type": inputs.boolean}


class ModelTermsFilter(Filter):
    def __init__(self, model, field_name="id", choices=None):
        self.model = model
        self.field_name = field_name
        super().__init__(choices=choices)

    @property
    def model_field(self):
        return getattr(self.model, self.field_name)

    def validate_parameter(self, value):
        if isinstance(value, ObjectId):
            return value
        try:
            return [self.model_field.to_mongo(v) for v in value.split(OR_SEPARATOR)]
        except Exception:
            raise ValueError('"{0}" is not valid identifier'.format(value))


class TemporalCoverageFilter(Filter):
    @classmethod
    def validate_parameter(cls, value):
        if not isinstance(value, str) or not RE_TIME_COVERAGE.match(value):
            msg = '"{0}" does not match YYYY-MM-DD-YYYY-MM-DD'.format(value)
            raise ValueError(msg)
        return value

    @classmethod
    def as_request_parser_kwargs(cls):
        return {
            "type": cls.validate_parameter,
            "help": "A date range expressed as start-end "
            "where both dates are in iso format "
            "(ie. YYYY-MM-DD-YYYY-MM-DD)",
        }
