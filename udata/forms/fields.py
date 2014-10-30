# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import tempfile

from bson import ObjectId, DBRef
from dateutil.parser import parse

from flask import url_for, request
from flask.ext.mongoengine.wtf import fields as mefields
from flask.ext.fs.mongo import ImageReference
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from wtforms import Form as WTForm, Field, validators, fields
from wtforms.fields import html5
from wtforms.utils import unset_value

from shapely.geometry import shape, MultiPolygon
from shapely.ops import cascaded_union

from . import widgets

from .validators import RequiredIf, optional

from udata.auth import current_user
from udata.models import db, Organization, SpatialCoverage, Territory, SPATIAL_GRANULARITIES
from udata.core.spatial import LEVELS
from udata.core.storages import tmp
from udata.i18n import lazy_gettext as _
from udata.utils import to_iso_date


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

    @property
    def hidden(self):
        return False

    def __call__(self, **kwargs):
        placeholder = kwargs.pop('placeholder', _(self.label.text))
        if placeholder:
            kwargs['placeholder'] = placeholder
        required = kwargs.pop('required', self.flags.required)
        if required is True:
            kwargs['required'] = required
        return super(FieldHelper, self).__call__(**kwargs)


class EmptyNone(object):
    def process_formdata(self, valuelist):
        '''Replace empty values by None'''
        super(EmptyNone, self).process_formdata(valuelist)
        self.data = self.data or None


class HiddenField(FieldHelper, EmptyNone, fields.HiddenField):
    pass


class StringField(FieldHelper, EmptyNone, fields.StringField):
    pass


class IntegerField(FieldHelper, fields.IntegerField):
    pass


class FormField(FieldHelper, fields.FormField):
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


class TmpFilename(fields.HiddenField):
    def _value(self):
        return u''


class BBoxField(fields.HiddenField):
    def _value(self):
        if self.data:
            return u','.join([str(x) for x in self.data])
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [int(float(x)) for x in valuelist[0].split(',')]
        else:
            self.data = None


class ImageForm(WTForm):
    filename = TmpFilename()
    bbox = BBoxField(validators=[optional()])


class ImageField(FieldHelper, fields.FormField):
    widget = widgets.ImagePicker()

    def __init__(self, label=None, validators=None, **kwargs):
        self.sizes = kwargs.pop('sizes', [100])
        self.placeholder = kwargs.pop('placeholder', 'default')
        super(ImageField, self).__init__(ImageForm, label, validators, **kwargs)

    def process(self, formdata, data=unset_value):
        self.src = data(100) if isinstance(data, ImageReference) else None
        super(ImageField, self).process(formdata, data)

    def populate_obj(self, obj, name):
        field = getattr(obj, name)
        bbox = self.form.bbox.data or None
        filename = self.form.filename.data or None
        if filename and filename in tmp:
            with tmp.open(filename) as infile:
                field.save(infile, filename, bbox=bbox)
            tmp.delete(filename)

    @property
    def endpoint(self):
        return url_for('storage.upload', name='tmp')


class UploadableURLField(URLField):
    widget = widgets.UploadableURL()

    def __init__(self, *args, **kwargs):
        storage = kwargs.pop('storage')
        self.endpoint = url_for('storage.upload', name=storage.name)
        super(UploadableURLField, self).__init__(*args, **kwargs)


class TextAreaField(FieldHelper, EmptyNone, fields.TextAreaField):
    pass


def nullable_text(value):
    return None if value == 'None' else fields.core.text_type(value)


class SelectField(FieldHelper, fields.SelectField):
    # widget = widgets.SelectPicker()

    def __init__(self, label=None, validators=None, coerce=nullable_text, **kwargs):
        # self._choices = kwargs.pop('choices')
        super(SelectField, self).__init__(label, validators, coerce, **kwargs)

    def iter_choices(self):
        localized_choices = [
            (value, _(label) if label else '', selected)
            for value, label, selected in super(SelectField, self).iter_choices()
        ]
        for value, label, selected in sorted(localized_choices, key=lambda c: c[1]):
            yield (value, label, selected)

    @property
    def choices(self):
        if callable(self._choices):
            return self._choices()
        else:
            return self._choices

    @choices.setter
    def choices(self, value):
        self._choices = value


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
                message = _('Tag "%(tag)s" must be between %(min)d and %(max)d characters long.',
                    min=MIN_TAG_LENGTH, max=MAX_TAG_LENGTH, tag=tag)
                raise validators.ValidationError(message)
            if not RE_TAG.match(tag):
                message = _('Tag "%(tag)s" must be alphanumeric characters or symbols: -_.', tag=tag)
                raise validators.ValidationError(message)


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


class ReuseListField(StringField):
    widget = widgets.ReuseAutocompleter()

    def _value(self):
        if self.data:
            return u','.join([str(reuse.id) for reuse in self.data])
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [DBRef('reuse', ObjectId(id.strip())) for id in valuelist[0].split(',') if id.strip()]
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


def level_key(territory):
    return LEVELS[territory.level]['position']


class TerritoriesField(StringField):
    widget = widgets.TerritoryAutocompleter()

    def _value(self):
        if self.data:
            return u','.join([str(t.id) for t in self.data])
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                ids = list(set([ObjectId(x.strip()) for x in valuelist[0].split(',') if x.strip()]))
                self.data = Territory.objects.in_bulk(ids).values()
            except Exception as e:
                raise ValueError(str(e))
        else:
            self.data = None


class SpatialCoverageForm(WTForm):
    territories = TerritoriesField(_('Territorial coverage'), description=_('A list of covered territories'))
    granularity = SelectField(_('Territorial granularity'), description=_('The size of the data increment'),
        choices=SPATIAL_GRANULARITIES.items(), default='other')

    def populate_obj(self, obj):
        super(SpatialCoverageForm, self).populate_obj(obj)
        try:
            territories = obj.territories
            polygon = cascaded_union([shape(t.geom) for t in territories])
            if polygon.geom_type == 'MultiPolygon':
                geom = polygon.__geo_interface__
            elif polygon.geom_type == 'Polygon':
                geom = MultiPolygon([polygon]).__geo_interface__
            else:
                geom = None
                # raise ValueError('Unsupported geometry type "{0}"'.format(polygon.geom_type))
            obj.territories = [t.reference() for t in sorted(territories, key=level_key)]
            obj.geom = geom
        except Exception as e:
            raise ValueError(str(e))


class SpatialCoverageField(FieldHelper, fields.FormField):
    def __init__(self, label=None, validators=None, **kwargs):
        default = kwargs.pop('default', lambda: SpatialCoverage())
        super(SpatialCoverageField, self).__init__(SpatialCoverageForm, label, validators, default=default, **kwargs)

    def populate_obj(self, obj, name):
        self._obj = self._obj or SpatialCoverage()
        super(SpatialCoverageField, self).populate_obj(obj, name)


class MarkdownField(FieldHelper, fields.TextAreaField):
    widget = widgets.MarkdownEditor()


class DateRangeField(FieldHelper, fields.StringField):
    widget = widgets.DateRangePicker()

    def _value(self):
        if self.data:
            return ' - '.join([to_iso_date(self.data.start), to_iso_date(self.data.end)])
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            start, end = valuelist[0].split(' - ')
            self.data = db.DateRange(
                start=parse(start, yearfirst=True).date(),
                end=parse(end, yearfirst=True).date(),
            )
        else:
            self.data = None


class PublishAsField(FieldHelper, fields.HiddenField):
    @property
    def hidden(self):
        return len(current_user.organizations) <= 0

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0].strip():
            self.data = DBRef('organization', ObjectId(valuelist[0].strip()))

    def populate_obj(self, obj, name):
        ret = super(PublishAsField, self).populate_obj(obj, name)
        if hasattr(obj, 'owner') and obj.owner and getattr(obj, name):
            obj.owner = None
        return ret


class ExtrasField(FieldHelper, fields.Field):
    def __init__(self, *args, **kwargs):
        if not 'extras' in kwargs:
            raise ValueError('extras parameter should be specified')
        self.extras = kwargs.pop('extras')
        super(ExtrasField, self).__init__(*args, **kwargs)

    def process_formdata(self, valuelist):
        if valuelist:
            data = valuelist[0]
            if isinstance(data, dict):
                self.data = data
            else:
                raise 'Unsupported datatype'
        else:
            self.data = {}

    def pre_validate(self, form):
        if self.data:
            try:
                self.extras.validate(self.data)
            except db.ValidationError as e:
                if e.errors:
                    self.errors.extend([': '.join((k, v)) for k, v in e.errors.items()])
                else:
                    self.errors.append(e.message)
