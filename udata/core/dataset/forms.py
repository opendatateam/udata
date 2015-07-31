# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, ModelForm, fields, validators, widgets
from udata.i18n import lazy_gettext as _

from udata.core.storages import resources

from .models import (
    Dataset, DatasetBadge, Resource, License, Checksum,
    UPDATE_FREQUENCIES, DEFAULT_FREQUENCY, RESOURCE_TYPES, CHECKSUM_TYPES,
    DATASET_BADGE_KINDS
)

__all__ = ('BadgeForm', 'DatasetForm', 'ResourceForm')


class DatasetForm(ModelForm):
    model_class = Dataset

    title = fields.StringField(_('Title'), [validators.required()])
    description = fields.MarkdownField(
        _('Description'), [validators.required()],
        description=_('The details about the dataset '
                      '(collection process, specifics...).'))
    license = fields.ModelSelectField(
        _('License'), model=License, allow_blank=True)
    frequency = fields.SelectField(
        _('Update frequency'),
        choices=UPDATE_FREQUENCIES.items(), default=DEFAULT_FREQUENCY,
        validators=[validators.optional()],
        description=_('The frequency at which data are updated.'))
    frequency_date = fields.DateTimeField(_('Expected frequency date'))
    temporal_coverage = fields.DateRangeField(
        _('Temporal coverage'),
        description=_('The period covered by the data'))
    spatial = fields.SpatialCoverageField(
        _('Spatial coverage'),
        description=_('The geographical area covered by the data.'))
    tags = fields.TagField(_('Tags'), description=_('Some taxonomy keywords'))
    private = fields.BooleanField(
        _('Private'),
        description=_('Restrict the dataset visibility to you or '
                      'your organization only.'))

    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_('Publish as'))
    extras = fields.ExtrasField(extras=Dataset.extras)


class ChecksumForm(Form):
    type = fields.SelectField(choices=zip(CHECKSUM_TYPES, CHECKSUM_TYPES),
                              default='sha1')
    value = fields.StringField()


class ChecksumWidget(object):
    def __call__(self, field, **kwargs):
        html = [
            '<div class="input-group checksum-group">',
            '<div class="input-group-btn">',
            field.form.type(class_='btn btn-default'),
            '</div>',
            field.value(class_='form-control'),
            '</div>'
        ]
        return widgets.HTMLString(''.join(html))


class ChecksumField(fields.FormField):
    widget = ChecksumWidget()

    def __init__(self, label=None, validators=None, **kwargs):
        super(ChecksumField, self).__init__(ChecksumForm, label, validators,
                                            **kwargs)

    def populate_obj(self, obj, name):
        self._obj = self._obj or Checksum()
        super(ChecksumField, self).populate_obj(obj, name)


class BadgeForm(ModelForm):
    model_class = DatasetBadge

    kind = fields.RadioField(
        _('Kind'), [validators.required()],
        choices=DATASET_BADGE_KINDS.items(),
        description=_('Kind of badge (pivotal-data, etc)'))


class ResourceForm(ModelForm):
    model_class = Resource

    title = fields.StringField(_('Title'), [validators.required()])
    description = fields.MarkdownField(_('Description'))
    type = fields.RadioField(
        _('Type'), [validators.required()],
        choices=RESOURCE_TYPES.items(), default='file',
        description=_('Whether the resource is an uploaded file, '
                      'a remote file or an API'))
    url = fields.UploadableURLField(
        _('URL'), [validators.required()], storage=resources)
    format = fields.StringField(
        _('Format'), widget=widgets.FormatAutocompleter())
    checksum = ChecksumField(_('Checksum'))
    mime = fields.StringField(
        _('Mime type'),
        description=_('The mime type associated to the extension. '
                      '(ex: text/plain)'))
    size = fields.IntegerField(
        _('Size'), [validators.optional()],
        description=_('The file size in bytes'))
    published = fields.DateTimeField(
        _('Publication date'),
        description=_('The publication date of the resource'))
