# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from datetime import datetime
from bson import ObjectId, DBRef

from wtforms import Form as WTForm, Field, validators, fields
from wtforms.fields import html5
from flask.ext.mongoengine.wtf import fields as mefields
from flask import url_for

from . import widgets

from .validators import RequiredIf

from udata.models import db
from udata.i18n import gettext as _


# _ = lambda s: s


RE_TAG = re.compile('^[\w \-.]*$', re.U)
MIN_TAG_LENGTH = 2
MAX_TAG_LENGTH = 128


class FieldHelper(object):
    @property
    def id(self):
        return '{0}-id'.format(self.name)

    @id.setter
    def id(self, value):
        pass

    def is_visible(self, user):
        return True

    def __call__(self, **kwargs):
        placeholder = kwargs.pop('placeholder', _(self.label.text))
        if placeholder:
            kwargs['placeholder'] = placeholder
        required = kwargs.pop('required', self.flags.required)
        if required is True:
            kwargs['required'] = required
        return super(FieldHelper, self).__call__(**kwargs)

    # def gettext(self, string):
    #     return i18n._(string)

    # _ = gettext


class EmptyNone(object):
    def process_formdata(self, valuelist):
        '''Replace empty values by None'''
        super(EmptyNone, self).process_formdata(valuelist)
        self.data = self.data or None


class StringField(FieldHelper, EmptyNone, fields.StringField):
    pass


class BooleanField(FieldHelper, fields.BooleanField):
    def __init__(self, *args, **kwargs):
        self.stacked = kwargs.pop('stacked', False)
        super(BooleanField, self).__init__(*args, **kwargs)


class RadioField(FieldHelper, fields.RadioField):
    def __init__(self, *args, **kwargs):
        self.stacked = kwargs.pop('stacked', False)
        super(RadioField, self).__init__(*args, **kwargs)


class FileField(FieldHelper, fields.FileField):
    pass


class URLField(FieldHelper, EmptyNone, html5.URLField):
    pass


class UploadableURLField(URLField):
    widget = widgets.UploadableURL()

    def __init__(self, *args, **kwargs):
        self.endpoint = url_for(kwargs.pop('endpoint'))
        super(UploadableURLField, self).__init__(*args, **kwargs)


class TextAreaField(FieldHelper, EmptyNone, fields.TextAreaField):
    pass


def nullable_text(value):
    return None if value == 'None' else fields.core.text_type(value)


class SelectField(FieldHelper, fields.SelectField):
    # widget = widgets.SelectPicker()

    def __init__(self, label=None, validators=None, coerce=nullable_text, **kwargs):
        super(SelectField, self).__init__(label, validators, coerce, **kwargs)

    def iter_choices(self):
        localized_choices = [
            (value, _(label) if label else '', selected)
            for value, label, selected in super(SelectField, self).iter_choices()
        ]
        for value, label, selected in sorted(localized_choices, key=lambda c: c[1]):
            yield (value, label, selected)


class ModelSelectField(FieldHelper, mefields.ModelSelectField):
    pass


class SelectMultipleField(FieldHelper, fields.SelectMultipleField):
    widget = widgets.SelectPicker(multiple=True)

    def iter_choices(self):
        localized_choices = [
            (value, self._(label) if label else '', selected)
            for value, label, selected in super(SelectMultipleField, self).iter_choices()
        ]
        for value, label, selected in sorted(localized_choices, key=lambda c: c[1]):
            yield (value, label, selected)


class TagField(StringField):
    widget = widgets.TagAutocompleter()

    def _value(self):
        if self.data:
            return u','.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = list(set([x.strip().lower() for x in valuelist[0].split(',') if x.strip()]))
        else:
            self.data = []

    def pre_validate(self, form):
        if not self.data:
            return
        for tag in self.data:
            if not MIN_TAG_LENGTH <= len(tag) <= MAX_TAG_LENGTH:
                message = self._('Tag "%(tag)s" must be between %(min)d and %(max)d characters long.')
                params = {'min': MIN_TAG_LENGTH, 'max': MAX_TAG_LENGTH, 'tag': tag}
                raise validators.ValidationError(message % params)
            if not RE_TAG.match(tag):
                message = self._('Tag "%s" must be alphanumeric characters or symbols: -_.')
                raise validators.ValidationError(message % tag)


class DatasetListField(StringField):
    widget = widgets.DatasetAutocompleter()

    def _value(self):
        if self.data:
            return u','.join([str(dataset.id) for dataset in self.data])
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [DBRef('dataset', ObjectId(id.strip())) for id in valuelist[0].split(',') if id.strip()]
        else:
            self.data = []


class UserField(StringField):
    def _value(self):
        if self.data:
            return unicode(self.data.id)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = DBRef('user', ObjectId(valuelist[0].strip()))
        else:
            self.data = None


class TerritoryField(StringField):
    widget = widgets.TerritoryAutocompleter()

    def _value(self):
        if self.data:
            return u','.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = list(set([x.strip() for x in valuelist[0].split(',') if x.strip()]))
        else:
            self.data = []

    def pre_validate(self, form):
        pass


class MarkdownField(FieldHelper, fields.TextAreaField):
    widget = widgets.MarkdownEditor()


class DateRangeField(FieldHelper, fields.StringField):
    widget = widgets.DateRangePicker()

    def _value(self):
        if self.data:
            return '{start:%Y-%m-%d} - {end:%Y-%m-%d}'.format(**self.data._data)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            start, end = valuelist[0].split(' - ')
            self.data = db.DateRange(
                start=datetime.strptime(start, '%Y-%m-%d').date(),
                end=datetime.strptime(end, '%Y-%m-%d').date(),
            )
        else:
            self.data = None


class PublishAsField(FieldHelper, Field):
    def is_visible(self, user):
        return len(user.organizations) > 0

    def process_data(self, value):
        self.data = value.id if isinstance(value, model.Group) else value

    def populate_obj(self, obj, name):
        fkey = '{0}_id'.format(name)
        if hasattr(obj, fkey):
            setattr(obj, fkey, self.data or None)
        else:
            setattr(obj, name, self.data)


class KeyValueForm(WTForm):
    key = StringField(_('Key'), [RequiredIf('value')])
    value = StringField(_('Value'))


class KeyValueField(FieldHelper, fields.FieldList):
    # widget = KeyValueWidget()
    def __init__(self, *args, **kwargs):
        kwargs['min_entries'] = kwargs.pop('min_entries', 1)
        super(KeyValueField, self).__init__(fields.FormField(KeyValueForm), *args, **kwargs)

    def process_data(self, values):
        print 'process_data', values
        return super(KeyValueField, self).process_data(values)

    def process(self, formdata, data=object()):
        print 'process', formdata, data
        return super(KeyValueField, self).process(formdata, data)

    @property
    def data(self):
        for f in self.entries:
            print f
        return [f.data for f in self.entries]

    # def process_data(self, values):
    #     if isinstance(values, dict):
    #         self.data = [(key, value) for key, value in values.items()]
    #     else:
    #         self.data = values

    # def _value(self):
    #     return self.data
        # if self.data:
        #     return u', '.join(self.data)
        # else:
        #     return u''
