# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import date, datetime

from mongoengine import EmbeddedDocument
from mongoengine.errors import ValidationError
from mongoengine.fields import DictField

log = logging.getLogger(__name__)


ALLOWED_TYPES = (basestring, int, float, bool, datetime, date, list)


class ExtrasField(DictField):
    def __init__(self, **kwargs):
        self.registered = {}
        super(ExtrasField, self).__init__()

    def register(self, key, extra):
        self.registered[key] = extra

    def validate(self, value):
        super(ExtrasField, self).validate(value)

        errors = {}
        for key, value in value.items():
            extra_cls = self.registered.get(key, DefaultExtra)

            try:
                if issubclass(extra_cls, EmbeddedDocument):
                    (value.validate()
                     if isinstance(value, extra_cls)
                     else extra_cls(**value).validate())
                else:
                    extra_cls().validate(value)
            except ValidationError as e:
                errors[key] = e.message

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


class Extra(object):
    def validate(self, value):
        raise NotImplemented


class DefaultExtra(Extra):
    def validate(self, value):
        if not isinstance(value, ALLOWED_TYPES):
            types = ', '.join(t.__name__ for t in ALLOWED_TYPES)
            raise ValidationError('Value should be an instance of: {types}',
                                  types=types)
        if isinstance(value, (list, tuple)):
            for _value in value:
                self.validate(_value)
