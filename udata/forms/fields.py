import uuid

from dateutil.parser import parse

from flask import url_for
from flask_mongoengine.wtf import fields as mefields
from flask_storage.mongo import ImageReference
from speaklater import is_lazy_string
from wtforms import Form as WTForm, Field as WTField, validators, fields, SubmitField  # noqa
from wtforms.utils import unset_value
from wtforms.widgets import TextInput
from wtforms_json import flatten_json

from . import widgets

from udata.auth import current_user, admin_permission
from udata.models import db, User, Organization, Dataset, Reuse, datastore, ContactPoint
from udata.core.storages import tmp
from udata.core.organization.permissions import OrganizationPrivatePermission
from udata.i18n import lazy_gettext as _
from udata import tags, uris
from udata.forms import ModelForm
from udata.utils import to_iso_date, get_by


class FieldHelper(object):
    def __init__(self, *args, **kwargs):
        self._preprocessors = kwargs.pop('preprocessors', [])
        super(FieldHelper, self).__init__(*args, **kwargs)
        self._form = kwargs.get('_form', None)

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
        placeholder = kwargs.pop('placeholder', self.label.text)
        if placeholder:
            kwargs['placeholder'] = placeholder
        required = kwargs.pop('required', self.flags.required)
        if required is True:
            kwargs['required'] = required
        return super(FieldHelper, self).__call__(**kwargs)

    def pre_validate(self, form):
        '''Calls preprocessors before pre_validation'''
        for preprocessor in self._preprocessors:
            preprocessor(form, self)
        super(FieldHelper, self).pre_validate(form)


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


class FloatField(FieldHelper, fields.FloatField):
    pass


class WTFDateTimeField(WTField):
    """
    Field copied from the code of wtforms extention dateutil removed in version 3.
    WTFDateTimeField represented by a text input, accepts all input text formats
    that `dateutil.parser.parse` will.
    :param parse_kwargs:
        A dictionary of keyword args to pass to the dateutil parse() function.
        See dateutil docs for available keywords.
    :param display_format:
        A format string to pass to strftime() to format dates for display.
    """
    widget = TextInput()

    def __init__(self, label=None, validators=None, parse_kwargs=None,
                 display_format='%Y-%m-%d %H:%M', **kwargs):
        super(WTFDateTimeField, self).__init__(label, validators, **kwargs)
        if parse_kwargs is None:
            parse_kwargs = {}
        self.parse_kwargs = parse_kwargs
        self.display_format = display_format

    def _value(self):
        if self.raw_data:
            return ' '.join(self.raw_data)
        else:
            return self.data and self.data.strftime(self.display_format) or ''

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            if not date_str:
                self.data = None
                raise validators.ValidationError(_('Please input a date/time value'))

            parse_kwargs = self.parse_kwargs.copy()
            if 'default' not in parse_kwargs:
                try:
                    parse_kwargs['default'] = self.default()
                except TypeError:
                    parse_kwargs['default'] = self.default
            try:
                self.data = parse(date_str, **parse_kwargs)
            except ValueError:
                self.data = None
                raise validators.ValidationError(_('Invalid date/time input'))


class DateField(WTFDateTimeField):
    """
    Same as the DateTimeField, but stores only the date portion.
    """
    def __init__(self, label=None, validators=None, parse_kwargs=None,
                 display_format='%Y-%m-%d', **kwargs):
        super(DateField, self).__init__(label, validators, parse_kwargs=parse_kwargs,
                                        display_format=display_format, **kwargs)

    def process_formdata(self, valuelist):
        super(DateField, self).process_formdata(valuelist)
        if self.data is not None and hasattr(self.data, 'date'):
            self.data = self.data.date()


class RolesField(Field):
    def process_formdata(self, valuelist):
        self.data = []
        for name in valuelist:
            role = datastore.find_role(name)
            if role is not None:
                self.data.append(role)
            else:
                raise validators.ValidationError(
                    _('The role {role} does not exist').format(role=name))


class DateTimeField(Field, WTFDateTimeField):
    def process_formdata(self, valuelist):
        if valuelist:
            dt = valuelist[0]
            self.data = parse(dt) if isinstance(dt, str) else dt


class UUIDField(Field):
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

    def process_formdata(self, valuelist):
        # We override this so that when no value is provided
        # the form doesn't think the value is `False` instead 
        # the value is not present and the model can keep the
        # existing value
        if not valuelist:
            return 

        super().process_formdata(valuelist)


class RadioField(FieldHelper, fields.RadioField):
    def __init__(self, *args, **kwargs):
        self.stacked = kwargs.pop('stacked', False)
        super(RadioField, self).__init__(*args, **kwargs)


class FileField(FieldHelper, fields.FileField):
    pass


class URLField(EmptyNone, Field):
    def pre_validate(self, form):
        if self.data:
            try:
                uris.validate(self.data)
            except uris.ValidationError:
                raise validators.ValidationError(_('Invalid URL'))
        return True

    def process_formdata(self, valuelist):
        super(URLField, self).process_formdata(valuelist)
        if self.data:
            self.data = self.data.strip()


class UploadableURLField(URLField):
    def __init__(self, *args, **kwargs):
        storage = kwargs.pop('storage')
        self.endpoint = url_for('storage.upload', name=storage.name)
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
        meta = kwargs['meta'] = kwargs.get('meta', {})
        meta['csrf'] = False
        return self.cls(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.cls, name)


class FormField(FieldHelper, fields.FormField):
    def __init__(self, form_class, *args, **kwargs):
        super(FormField, self).__init__(FormWrapper(form_class),
                                        *args, **kwargs)
        self.prefix = '{0}-'.format(self.name)
        self._formdata = None

    def process(self, formdata, data=unset_value, **kwargs):
        self._formdata = formdata
        return super(FormField, self).process(formdata, data=data, **kwargs)

    def validate(self, form, extra_validators=tuple()):
        if extra_validators:
            raise TypeError('FormField does not accept in-line validators, '
                            'as it gets errors from the enclosed form.')

        # Run normal validation only if there is data for this form
        if self.has_data:
            return self.form.validate()
        return True

    def populate_obj(self, obj, name):
        if not self.has_data:
            return
        if getattr(self.form_class, 'model_class', None) and not self._obj:
            self._obj = self.form_class.model_class()
        super(FormField, self).populate_obj(obj, name)

    @property
    def data(self):
        return self.form.data if self.has_data else None

    @property
    def has_data(self):
        return self._formdata and any(
            k.startswith(self.prefix) for k in self._formdata
        )


class TmpFilename(Field):
    def _value(self):
        return ''


class BBoxField(Field):
    def _value(self):
        if self.data:
            return ','.join([str(x) for x in self.data])
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [int(float(x)) for x in valuelist[0].split(',')]
        else:
            self.data = None


class ImageForm(WTForm):
    filename = TmpFilename()
    bbox = BBoxField(validators=[validators.optional()])


class ImageField(FormField):
    def __init__(self, label=None, validators=None, **kwargs):
        self.sizes = kwargs.pop('sizes', [100])
        self.placeholder = kwargs.pop('placeholder', 'default')
        super(ImageField, self).__init__(ImageForm, label, validators,
                                         **kwargs)

    def process(self, formdata, data=unset_value, **kwargs):
        self.src = data(100) if isinstance(data, ImageReference) else None
        super(ImageField, self).process(formdata, data, **kwargs)

    def populate_obj(self, obj, name):
        field = getattr(obj, name)
        bbox = self.form.bbox.data or None
        filename = self.form.filename.data or None
        if filename and filename in tmp:
            with tmp.open(filename, 'rb') as infile:
                field.save(infile, filename, bbox=bbox)
            tmp.delete(filename)

    @property
    def endpoint(self):
        return url_for('storage.upload', name='tmp')


def nullable_text(value):
    return None if value == 'None' else str(value)


class SelectField(FieldHelper, fields.SelectField):
    def __init__(self, label=None, validators=None, coerce=nullable_text,
                 **kwargs):
        # self._choices = kwargs.pop('choices')
        super(SelectField, self).__init__(label, validators, coerce, **kwargs)

    @staticmethod
    def localize_label(label):
        if not label:
            return ''
        if is_lazy_string(label):
            return label
        return _(label)

    def iter_choices(self):
        localized_choices = [
            (value, self.localize_label(label), selected)
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


class TagField(Field):
    def _value(self):
        if self.data:
            return ','.join(self.data)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist and len(valuelist) > 1:
            self.data = [tags.slug(value) for value in valuelist]
        elif valuelist:
            self.data = tags.tags_list(valuelist[0])
        else:
            self.data = []

    def pre_validate(self, form):
        if not self.data:
            return
        for tag in self.data:
            if not tags.MIN_TAG_LENGTH <= len(tag) <= tags.MAX_TAG_LENGTH:
                message = _(
                    'Tag "%(tag)s" must be between %(min)d '
                    'and %(max)d characters long.',
                    min=tags.MIN_TAG_LENGTH,
                    max=tags.MAX_TAG_LENGTH, tag=tag)
                raise validators.ValidationError(message)


def clean_oid(oid, model):
    if (isinstance(oid, dict) and 'id' in oid):
        return clean_oid(oid['id'], model)
    else:
        try:
            # Prevalidation is required as to_python is failsafe
            # and returns the original value on exception
            model.id.validate(oid)
            return model.id.to_python(oid)
        except Exception:  # Catch all exceptions as model.type is not predefined
            raise ValueError('Unsupported identifier: {0}'.format(oid))


class ModelFieldMixin(object):
    model = None

    def __init__(self, *args, **kwargs):
        self.model = kwargs.pop('model', self.model)
        super(ModelFieldMixin, self).__init__(*args, **kwargs)

    def _value(self):
        if self.data:
            return str(self.data.id)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist and len(valuelist) == 1 and valuelist[0]:
            try:
                id = clean_oid(valuelist[0], self.model)
                self.data = self.model.objects.get(id=id)
            except self.model.DoesNotExist:
                message = _('{0} does not exists').format(self.model.__name__)
                raise validators.ValidationError(message)


class ModelField(Field):
    def process(self, formdata, data=unset_value, **kwargs):
        if formdata:
            # Process prefixed values as in FormField
            newdata = {}
            prefix = self.short_name + '-'
            for key in list(formdata.keys()):
                if key.startswith(prefix):
                    value = formdata.pop(key)
                    newdata[key.replace(prefix, '')] = value
            if newdata:
                formdata.add(self.short_name, newdata)
        super(ModelField, self).process(formdata, data, **kwargs)

    def process_formdata(self, valuelist):
        if not valuelist or len(valuelist) != 1 or not valuelist[0]:
            return
        specs = valuelist[0]
        model_field = getattr(self._form.model_class, self.name)
        if isinstance(specs, str):
            specs = {'id': specs}
        elif not specs.get('id', None):
            raise validators.ValidationError(_('Missing "id" field'))

        if isinstance(model_field, db.ReferenceField):
            expected_model = str(model_field.document_type.__name__)
            if 'class' not in specs:
                specs['class'] = expected_model
            elif specs['class'] != expected_model:
                msg = _('Expect a "{0}" class but "{1}" was found').format(
                    expected_model, specs['class']
                )
                raise validators.ValidationError(msg)
        elif isinstance(model_field, db.GenericReferenceField):
            if 'class' not in specs:
                msg = _('Expect both class and identifier')
                raise validators.ValidationError(msg)

        # No try/except required
        # In case of error, ValueError is raised
        # and is properly handled as form validation error
        model = db.resolve_model(specs['class'])
        oid = clean_oid(specs, model)

        try:
            self.data = model.objects.only('id').get(id=oid)
        except db.DoesNotExist:
            label = '{0}({1})'.format(model.__name__, oid)
            msg = _('{0} does not exists').format(label)
            raise validators.ValidationError(msg)

    def pre_validate(self, form):
        # If any error happen during process, we raise StopValidation here
        # to prevent "DataRequired" validator from clearing errors
        if self.errors:
            raise validators.StopValidation()
        super(ModelField, self).pre_validate(form)


class ModelChoiceField(StringField):
    models = None

    def __init__(self, *args, **kwargs):
        self.models = kwargs.pop('models', self.models)
        super(ModelChoiceField, self).__init__(*args, **kwargs)

    def _value(self):
        if self.data:
            return str(self.data.id)
        else:
            return ''

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
            return ','.join([str(o.id) for o in self.data])
        else:
            return ''

    def process_formdata(self, valuelist):
        if not valuelist:
            return []
        if len(valuelist) == 1 and isinstance(valuelist[0], str):
            oids = [clean_oid(id, self.model)
                    for id in valuelist[0].split(',') if id]
        else:
            oids = [clean_oid(id, self.model) for id in valuelist]
        self.data = self.fetch_objects(oids)

    def fetch_objects(self, oids):
        '''
        This methods is used to fetch models
        from a list of identifiers.

        Default implementation performs a bulk query on identifiers.

        Override this method to customize the objects retrieval.
        '''
        objects = self.model.objects.in_bulk(oids)
        if len(objects.keys()) != len(oids):
            non_existants = set(oids) - set(objects.keys())
            msg = _('Unknown identifiers: {identifiers}').format(
                identifiers=', '.join(str(ne) for ne in non_existants))
            raise validators.ValidationError(msg)

        return [objects[id] for id in oids]


class NestedModelList(fields.FieldList):
    def __init__(self, model_form, *args, **kwargs):
        super(NestedModelList, self).__init__(FormField(model_form),
                                              *args,
                                              **kwargs)
        self.nested_form = model_form
        self.nested_model = model_form.model_class
        self.data_submitted = False
        self.initial_data = []
        self.prefix = '{0}-'.format(self.name)

    def process(self, formdata, data=unset_value, **kwargs):
        self._formdata = formdata
        self.initial_data = data
        self.is_list_data = formdata and self.name in formdata
        self.is_dict_data = formdata and any(
            k.startswith(self.prefix) for k in formdata
        )
        self.has_data = self.is_list_data or self.is_dict_data
        if self.has_data:
            super(NestedModelList, self).process(formdata, data, **kwargs)
        else:
            self.entries = []
            # super(NestedModelList, self).process(None, data, **kwargs)

    def validate(self, form, extra_validators=tuple()):
        '''Perform validation only if data has been submitted'''
        if not self.has_data:
            return True
        if self.is_list_data:
            if not isinstance(self._formdata[self.name], (list, tuple)):
                return False
        return super(NestedModelList, self).validate(form, extra_validators)

    def populate_obj(self, obj, name):
        if not self.has_data:
            return

        initial_values = getattr(obj, name, [])
        new_values = []

        class Holder(object):
            pass

        holder = Holder()

        for idx, field in enumerate(self):
            initial = None
            if hasattr(self.nested_model, 'id') and 'id' in field.data:
                id = self.nested_model.id.to_python(field.data['id'])
                initial = get_by(initial_values, 'id', id)

            holder.nested = initial or self.nested_model()
            field.populate_obj(holder, 'nested')
            new_values.append(holder.nested)

        setattr(obj, name, new_values)

    def _add_entry(self, formdata=None, data=unset_value, index=None):
        '''
        Fill the form with previous data if necessary to handle partial update
        '''
        if formdata:
            prefix = '-'.join((self.name, str(index)))
            basekey = '-'.join((prefix, '{0}'))
            idkey = basekey.format('id')
            if prefix in formdata:
                formdata[idkey] = formdata.pop(prefix)
            if hasattr(self.nested_model, 'id') and idkey in formdata:
                id = self.nested_model.id.to_python(formdata[idkey])
                data = get_by(self.initial_data, 'id', id)

                initial = flatten_json(self.nested_form,
                                       data.to_mongo(),
                                       prefix)

                for key, value in initial.items():
                    if key not in formdata:
                        formdata[key] = value
            else:
                data = None
        return super(NestedModelList, self)._add_entry(formdata, data, index)


class DatasetListField(ModelList, Field):
    model = Dataset


class ReuseListField(ModelList, Field):
    model = Reuse


class UserField(ModelFieldMixin, Field):
    model = User


class DatasetField(ModelFieldMixin, Field):
    model = Dataset


class MarkdownField(FieldHelper, fields.TextAreaField):
    widget = widgets.MarkdownEditor()


class DateRangeField(Field):
    def _value(self):
        if self.data:
            return ' - '.join([to_iso_date(self.data.start),
                               to_iso_date(self.data.end)])
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            value = valuelist[0]
            if isinstance(value, str):
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
    if current_user.is_authenticated:
        return current_user._get_current_object()


class CurrentUserField(ModelFieldMixin, Field):
    model = User

    def __init__(self, *args, **kwargs):
        kwargs['default'] = kwargs.pop('default', default_owner)
        super(CurrentUserField, self).__init__(*args, **kwargs)

    def process(self, formdata, data=unset_value, **kwargs):
        if formdata and self.name in formdata and formdata[self.name] is None:
            formdata.pop(self.name)  # None value does not trigger default
        return super(CurrentUserField, self).process(formdata, data, **kwargs)

    def pre_validate(self, form):
        if self.data:
            if current_user.is_anonymous:
                raise validators.ValidationError(
                    _('You must be authenticated'))
            elif not admin_permission and current_user.id != self.data.id:
                raise validators.ValidationError(
                    _('You can only set yourself as owner'))
        return True


class PublishAsField(ModelFieldMixin, Field):
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
            if not current_user.is_authenticated:
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


class ContactPointField(ModelFieldMixin, Field):
    model = ContactPoint

    def __init__(self, *args, **kwargs):
        super(ContactPointField, self).__init__(*args, **kwargs)


def field_parse(cls, value, *args, **kwargs):
    kwargs['_form'] = WTForm()
    kwargs['name'] = 'extra'
    field = cls(*args, **kwargs)
    field.process_formdata([value])
    return field.data


class ExtrasField(Field):
    KNOWN_TYPES = {
        db.DateTimeField: DateTimeField,
        db.DateField: DateField,
        db.IntField: IntegerField,
        db.BooleanField: BooleanField,
        db.StringField: StringField,
        db.FloatField: FloatField,
        db.URLField: URLField,
        db.UUIDField: UUIDField,
    }

    def __init__(self, *args, **kwargs):
        super(ExtrasField, self).__init__(*args, **kwargs)
        if not isinstance(self._form, ModelForm):
            raise ValueError('ExtrasField can only be used within a ModelForm')
        model_field = getattr(self._form.model_class, self.short_name, None)
        if not model_field or not isinstance(model_field, db.ExtrasField):
            msg = 'Form ExtrasField can only be mapped to a model ExtraField'
            raise ValueError(msg)

    @property
    def extras(self):
        '''Getter to the model extras field'''
        return getattr(self._form.model_class, self.short_name)

    def parse(self, data):
        '''Parse fields and store individual errors'''
        self.field_errors = {}
        return dict(
            (k, self._parse_value(k, v)) for k, v in data.items()
        )

    def _parse_value(self, key, value):
        if key not in self.extras.registered:
            return value
        expected = self.extras.registered[key]
        if expected in self.KNOWN_TYPES:
            try:
                return field_parse(self.KNOWN_TYPES[expected], value)
            except (validators.ValidationError, ValueError) as e:
                self.field_errors[key] = getattr(e, 'message', str(e))
        else:
            return value

    def process_formdata(self, valuelist):
        if valuelist:
            data = valuelist[0]
            if isinstance(data, dict):
                self.data = self.parse(data)
            else:
                raise ValueError('Unsupported data type')
        else:
            self.data = self.parse(self.data or {})

    def validate(self, form, extra_validators=tuple()):
        if self.process_errors:
            self.errors = list(self.process_errors)
        elif getattr(self, 'field_errors', None):
            self.errors = self.field_errors
        elif self.data:
            try:
                self.extras.validate(self.data)
            except db.ValidationError as e:
                self.errors = e.errors if e.errors else [e.message]
        else:
            self.errors = None

        return not bool(self.errors)


class DictField(Field):
    def process_formdata(self, valuelist):
        if valuelist:
            data = valuelist[0]
            if isinstance(data, dict):
                self.data = data
            else:
                raise ValueError('Unsupported data type')
