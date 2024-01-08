import logging

from datetime import date, datetime

from mongoengine import EmbeddedDocument
from mongoengine.fields import DictField, BaseField

log = logging.getLogger(__name__)


ALLOWED_TYPES = (str, int, float, bool, datetime, date, list)


class ExtrasField(DictField):
    def __init__(self, **kwargs):
        self.registered = {}
        super(ExtrasField, self).__init__()

    def register(self, key, dbtype):
        '''Register a DB type to add constraint on a given extra key'''
        if not issubclass(dbtype, (BaseField, EmbeddedDocument)):
            msg = 'ExtrasField can only register MongoEngine fields'
            raise TypeError(msg)
        self.registered[key] = dbtype

    def validate(self, values):
        super(ExtrasField, self).validate(values)

        errors = {}
        for key, value in values.items():
            extra_cls = self.registered.get(key)

            if not extra_cls:
                if not isinstance(value, ALLOWED_TYPES):
                    types = ', '.join(t.__name__ for t in ALLOWED_TYPES)
                    msg = 'Value should be an instance of: {types}'
                    errors[key] = msg.format(types=types)
                continue

            try:
                if issubclass(extra_cls, EmbeddedDocument):
                    (value.validate()
                     if isinstance(value, extra_cls)
                     else extra_cls(**value).validate())
                else:
                    extra_cls().validate(value)
            except Exception as e:
                errors[key] = getattr(e, 'message', str(e))

        if errors:
            self.error('Unsupported types', errors=errors)

    def __call__(self, key):
        def inner(cls):
            self.register(key, cls)
            return cls
        return inner

    def to_python(self, value):
        if isinstance(value, EmbeddedDocument):
            return value
        return super(ExtrasField, self).to_python(value)


class OrganizationExtrasField(ExtrasField):
    def __init__(self, **kwargs):
        super(OrganizationExtrasField, self).__init__()

    def validate(self, values):
        super(ExtrasField, self).validate(values)

        errors = {}

        mandatory_keys = ["title", "description", "type"]
        optional_keys = ["choices"]
        valid_types = ["str", "int", "float", "bool", "datetime", "date", "choice"]

        for elem in values.get('custom', []):
            mandatory_keys_set = set(mandatory_keys)
            optional_keys_set = set(optional_keys)
            dict_keys_set = set(elem.keys())
            # Check if all mandatory keys are in the dictionary
            if not mandatory_keys_set.issubset(dict_keys_set):
                errors['custom'] = 'The dictionary does not contain the mandatory keys.'
            # Combine mandatory and optional keys
            all_allowed_keys = mandatory_keys_set.union(optional_keys_set)
            # Check if there are any keys in the dictionary that are neither mandatory nor optional
            extra_keys = dict_keys_set - all_allowed_keys
            # If there are no extra keys, the dictionary is valid
            if len(extra_keys) == 0:
                if elem.get("type") not in valid_types:
                    errors['type'] = ('Type \'{type}\' of \'{title}\' should be one of: {types}'
                                      .format(type=elem.get("type"), title=elem.get("title"), types=valid_types))
            else:
                errors['custom'] = 'The dictionary does contains extra keys than allowed ones.'

            # If the "choices" key exists, check that it's not an empty list
            if "choices" in elem and not elem["choices"]:
                errors['custom'] = 'The \'choices\' keys cannot be an empty list.'

        if errors:
            self.error('Custom extras error', errors=errors)
