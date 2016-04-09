# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from wtforms import validators
from wtforms.validators import *  # noqa
from wtforms.validators import ValidationError, StopValidation  # noqa


def _(s):
    return s


class RequiredIf(validators.DataRequired):
    '''
    A validator which makes a field required
    only if another field is set and has a truthy value.
    '''
    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(RequiredIf, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception(
                'No field named "%s" in form' % self.other_field_name)
        if bool(other_field.data):
            super(RequiredIf, self).__call__(form, field)


class Requires(object):
    '''
    A validator which makes a field required another field.
    '''
    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(Requires, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        if not field.data:
            return
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception(
                'No field named "%s" in form' % self.other_field_name)
        if not bool(other_field.data):
            msg = field._('This field requires "%(name)s" to be set')
            raise validators.ValidationError(
                msg % {'name': field._(other_field.label.text)})


class RequiredIfVal(validators.DataRequired):
    '''
    A validator which makes a field required
    only if another field is set and has a specified value.
    '''
    def __init__(self, other_field_name, expected_value, *args, **kwargs):
        self.other_field_name = other_field_name
        self.expected_values = (
            expected_value
            if isinstance(expected_value, (list, tuple))
            else (expected_value,)
        )
        super(RequiredIfVal, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception(
                'No field named "%s" in form' % self.other_field_name)
        if other_field.data in self.expected_values:
            super(RequiredIfVal, self).__call__(form, field)
