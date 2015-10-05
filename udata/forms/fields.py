# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
import uuid

from dateutil.parser import parse

from flask import url_for
from flask.ext.mongoengine.wtf import fields as mefields
from flask.ext.fs.mongo import ImageReference
from wtforms import Form as WTForm, Field as WTField, validators, fields
from wtforms.fields import html5
from wtforms.utils import unset_value

from . import widgets

from udata.auth import current_user, admin_permission
from udata.models import (
    db, User, SpatialCoverage, Organization, GeoZone, spatial_granularities,
    Dataset, Reuse
)
from udata.core.storages import tmp
from udata.core.organization.permissions import OrganizationPrivatePermission
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


class Field(FieldHelper, WTField):
    pass


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


class DateTimeField(Field, fields.DateTimeField):

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = parse(valuelist[0])


class UUIDField(Field, fields.HiddenField):
    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = uuid.UUID(valuelist[0])
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid UUID'))


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
    bbox = BBoxField(validators=[validators.optional()])


class ImageField(FieldHelper, fields.FormField):
    widget = widgets.ImagePicker()

    def __init__(self, label=None, validators=None, **kwargs):
        self.sizes = kwargs.pop('sizes', [100])
        self.placeholder = kwargs.pop('placeholder', 'default')
        super(ImageField, self).__init__(ImageForm, label, validators,
                                         **kwargs)

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
        self.checkurl = url_for('api.checkurl')
        super(UploadableURLField, self).__init__(*args, **kwargs)


class TextAreaField(FieldHelper, EmptyNone, fields.TextAreaField):
    pass


class FormWrapper(object):
    '''
    Wrap FormField nested form class to handle both
    JSON provisionning from wtforms-json
    and CSRF disabled from flask-wtf
    '''
    def __init__(self, cls):
        self.cls = cls

    def __call__(self, *args, **kwargs):
        kwargs['csrf_enabled'] = False
        return self.cls(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.cls, name)


class FormField(FieldHelper, fields.FormField):
    def __init__(self, form_class, *args, **kwargs):
        super(FormField, self).__init__(FormWrapper(form_class),
                                        *args, **kwargs)


def nullable_text(value):
    return None if value == 'None' else fields.core.text_type(value)


class SelectField(FieldHelper, fields.SelectField):
    # widget = widgets.SelectPicker()

    def __init__(self, label=None, validators=None, coerce=nullable_text,
                 **kwargs):
        # self._choices = kwargs.pop('choices')
        super(SelectField, self).__init__(label, validators, coerce, **kwargs)

    def iter_choices(self):
        localized_choices = [
            (value, _(label) if label else '', selected)
            for value, label, selected
            in super(SelectField, self).iter_choices()
        ]
        for value, label, selected in sorted(localized_choices,
                                             key=lambda c: c[1]):
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
            for value, label, selected
            in super(SelectMultipleField, self).iter_choices()
        ]
        for value, label, selected in sorted(localized_choices,
                                             key=lambda c: c[1]):
            yield (value, label, selected)


class TagField(StringField):
    widget = widgets.TagAutocompleter()

    def _value(self):
        if self.data:
            return u','.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist and len(valuelist) > 1:
            self.data = valuelist
        elif valuelist:
            self.data = list(set([
                x.strip().lower()
                for x in valuelist[0].split(',') if x.strip()]))
        else:
            self.data = []

    def pre_validate(self, form):
        if not self.data:
            return
        for tag in self.data:
            if not MIN_TAG_LENGTH <= len(tag) <= MAX_TAG_LENGTH:
                message = _(
                    'Tag "%(tag)s" must be between %(min)d '
                    'and %(max)d characters long.',
                    min=MIN_TAG_LENGTH, max=MAX_TAG_LENGTH, tag=tag)
                raise validators.ValidationError(message)
            if not RE_TAG.match(tag):
                message = _('Tag "%(tag)s" must be alphanumeric characters '
                            'or symbols: -_.', tag=tag)
                raise validators.ValidationError(message)


def clean_oid(oid, model):
    if (isinstance(oid, dict) and 'id' in oid):
        return clean_oid(oid['id'], model)
    else:
        try:
            return model.id.to_python(oid)
        except:  # Catch all exceptions as model.type is not predefined
            raise ValueError('Unsupported identifier: ' + oid)


class ModelField(object):
    model = None

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', self.model)
        super(ModelField, self).__init__(*args, **kwargs)

    def _value(self):
        if self.data:
            return unicode(self.data.id)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist and len(valuelist) == 1 and valuelist[0]:
            try:
                self.data = self.model.objects.get(id=clean_oid(valuelist[0],
                                                                self.model))
            except self.model.DoesNotExist:
                message = _('{0} does not exists').format(self.model.__name__)
                raise validators.ValidationError(message)


class ModelChoiceField(StringField):
    models = None

    def __init__(self, *args, **kwargs):
        self.models = kwargs.pop('models', self.models)
        super(ModelChoiceField, self).__init__(*args, **kwargs)

    def _value(self):
        if self.data:
            return unicode(self.data.id)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist and len(valuelist) == 1 and valuelist[0]:
            for model in self.models:
                try:
                    self.data = model.objects.get(id=clean_oid(valuelist[0],
                                                               model))
                except model.DoesNotExist:
                    pass
            if not self.data:
                message = _('Model for {0} not found').format(valuelist[0])
                raise validators.ValidationError(message)


class ModelList(object):
    model = None

    def _value(self):
        if self.data:
            return u','.join([str(o.id) for o in self.data])
        else:
            return u''

    def process_formdata(self, valuelist):
        if not valuelist:
            return []
        if len(valuelist) > 1:
            oids = [clean_oid(id, self.model) for id in valuelist]
        elif isinstance(valuelist[0], basestring):
            oids = [
                clean_oid(id, self.model)
                for id in valuelist[0].split(',') if id]
        else:
            raise validators.ValidationError(
                'Unsupported form parameter: ' + valuelist)

        objects = self.model.objects.in_bulk(oids)
        if len(objects.keys()) != len(oids):
            non_existants = set(oids) - set(objects.keys())
            raise validators.ValidationError(
                'Unknown identifiers: ' + ', '.join(non_existants))

        self.data = [objects[id] for id in oids]


class DatasetListField(ModelList, StringField):
    model = Dataset
    widget = widgets.DatasetAutocompleter()


class ReuseListField(ModelList, StringField):
    model = Reuse
    widget = widgets.ReuseAutocompleter()


class UserField(ModelField, StringField):
    model = User


class DatasetOrReuseField(ModelChoiceField, StringField):
    models = [Dataset, Reuse]


class DatasetOrOrganizationField(ModelChoiceField, StringField):
    models = [Dataset, Organization]


class DatasetField(ModelField, StringField):
    model = Dataset


class ZonesField(ModelList, StringField):
    model = GeoZone
    widget = widgets.ZonesAutocompleter()


class SpatialCoverageForm(WTForm):
    zones = ZonesField(_('Spatial coverage'),
                       description=_('A list of covered territories'))
    granularity = SelectField(_('Spatial granularity'),
                              description=_('The size of the data increment'),
                              choices=lambda: spatial_granularities,
                              default='other')


class SpatialCoverageField(FieldHelper, fields.FormField):
    def __init__(self, label=None, validators=None, **kwargs):
        default = kwargs.pop('default', lambda: SpatialCoverage())
        super(SpatialCoverageField, self).__init__(
            SpatialCoverageForm, label, validators, default=default, **kwargs)

    def populate_obj(self, obj, name):
        self._obj = self._obj or SpatialCoverage()
        super(SpatialCoverageField, self).populate_obj(obj, name)


class MarkdownField(FieldHelper, fields.TextAreaField):
    widget = widgets.MarkdownEditor()


class DateRangeField(FieldHelper, fields.StringField):
    widget = widgets.DateRangePicker()

    def _value(self):
        if self.data:
            return ' - '.join([to_iso_date(self.data.start),
                               to_iso_date(self.data.end)])
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            value = valuelist[0]
            if isinstance(value, basestring):
                start, end = value.split(' - ')
                self.data = db.DateRange(
                    start=parse(start, yearfirst=True).date(),
                    end=parse(end, yearfirst=True).date(),
                )
            elif 'start' in value and 'end' in value:
                self.data = db.DateRange(
                    start=parse(value['start'], yearfirst=True).date(),
                    end=parse(value['end'], yearfirst=True).date(),
                )
            else:
                raise validators.ValidationError(
                    _('Unable to parse date range'))
        else:
            self.data = None


def default_owner():
    '''Default to current_user if authenticated'''
    if current_user.is_authenticated():
        return current_user._get_current_object()


class CurrentUserField(FieldHelper, ModelField, fields.HiddenField):
    model = User

    def __init__(self, *args, **kwargs):
        default = kwargs.pop('default', default_owner)
        super(CurrentUserField, self).__init__(default=default,
                                               *args, **kwargs)

    def pre_validate(self, form):
        if self.data:
            if current_user.is_anonymous():
                raise validators.ValidationError(
                    _('You must be authenticated'))
            elif not admin_permission and current_user.id != self.data.id:
                raise validators.ValidationError(
                    _('You can only set yourself as owner'))
        return True


class PublishAsField(FieldHelper, ModelField, fields.HiddenField):
    model = Organization
    owner_field = 'owner'

    def __init__(self, *args, **kwargs):
        self.owner_field = kwargs.pop('owner_field', self.owner_field)
        super(PublishAsField, self).__init__(*args, **kwargs)

    @property
    def hidden(self):
        return len(current_user.organizations) <= 0

    def pre_validate(self, form):
        if self.data:
            if not current_user.is_authenticated():
                raise validators.ValidationError(
                    _('You must be authenticated'))
            elif not OrganizationPrivatePermission(self.data).can():
                raise validators.ValidationError(
                    _("Permission denied for this organization"))
            # Ensure either owner field or this field value is unset
            owner_field = form._fields[self.owner_field]
            if self.raw_data:
                owner_field.data = None
            elif getattr(form._obj, self.short_name) and not owner_field.data:
                pass
            else:
                self.data = None
        return True


class ExtrasField(FieldHelper, fields.Field):
    def __init__(self, *args, **kwargs):
        if 'extras' not in kwargs:
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
            self.data = self.data or {}

    def pre_validate(self, form):
        if self.data:
            try:
                self.extras.validate(self.data)
            except db.ValidationError as e:
                if e.errors:
                    self.errors.extend([': '.join((k, v))
                                        for k, v in e.errors.items()])
                else:
                    self.errors.append(e.message)
