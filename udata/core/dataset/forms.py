# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, ModelForm, UserModelForm, UserModelFormMixin, fields, validators, widgets
from udata.i18n import lazy_gettext as _

from udata.core.storages import resources

from .models import Dataset, Resource, License, UPDATE_FREQUENCIES, RESOURCE_TYPES

__all__ = ('DatasetForm', 'DatasetCreateForm', 'ResourceForm', 'CommunityResourceForm', 'DatasetExtraForm')


class DatasetForm(UserModelForm):
    model_class = Dataset

    title = fields.StringField(_('Title'), [validators.required()])
    description = fields.MarkdownField(_('Description'), [validators.required()],
        description=_('The details about the dataset (collection process, specifics...).'))
    license = fields.ModelSelectField(_('License'), model=License, allow_blank=True)
    frequency = fields.SelectField(_('Update frequency'),
        choices=UPDATE_FREQUENCIES.items(), validators=[validators.optional()],
        description=_('The frequency at which data are updated.'))
    temporal_coverage = fields.DateRangeField(_('Temporal coverage'),
        description=_('The period covered by the data'))
    spatial = fields.SpatialCoverageField(_('Spatial coverage'),
        description=_('The geographical area covered by the data.'))
    tags = fields.TagField(_('Tags'), description=_('Some taxonomy keywords'))
    private = fields.BooleanField(_('Private'),
        description=_('Restrict the dataset visibility to you or your organization only.'))


class DatasetCreateForm(DatasetForm):
    organization = fields.PublishAsField(_('Publish as'))


class DatasetFullForm(DatasetForm):
    organization = fields.PublishAsField()
    extras = fields.ExtrasField(extras=Dataset.extras)


class ResourceForm(ModelForm):
    model_class = Resource

    title = fields.StringField(_('Title'), [validators.required()])
    description = fields.MarkdownField(_('Description'), [validators.required()])
    type = fields.RadioField(_('Type'), [validators.required()],
        choices=RESOURCE_TYPES.items(), default='file',
        description=_('Whether the resource is an uploaded file, a remote file or an API'))
    url = fields.UploadableURLField(_('URL'), [validators.required()], storage=resources)
    format = fields.StringField(_('Format'), widget=widgets.FormatAutocompleter())
    checksum = fields.StringField(_('Checksum'))
    mime = fields.StringField(_('Mime type'), description=_('The mime type associated to the extension'))
    size = fields.IntegerField(_('Size'), description=_('The file size in octets'))


class CommunityResourceForm(UserModelFormMixin, ResourceForm):
    pass


class DatasetExtraForm(Form):
    key = fields.StringField(_('Key'), [validators.required()])
    value = fields.StringField(_('Value'), [validators.required()])
    old_key = fields.StringField(_('Old key'))
