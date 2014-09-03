# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, ModelForm, UserModelForm, fields, validators, widgets
from udata.i18n import lazy_gettext as _

from .models import Dataset, Resource, License, UPDATE_FREQUENCIES

__all__ = ('DatasetForm', 'DatasetCreateForm', 'ResourceForm', 'DatasetExtraForm')


class DatasetForm(UserModelForm):
    model_class = Dataset

    title = fields.StringField(_('Title'), [validators.required()])
    description = fields.MarkdownField(_('Description'), [validators.required()])
    license = fields.ModelSelectField(_('License'), model=License, allow_blank=True)
    frequency = fields.SelectField(_('Update frequency'),
        choices=UPDATE_FREQUENCIES.items(), validators=[validators.optional()])
    temporal_coverage = fields.DateRangeField(_('Temporal coverage'))
    spatial = fields.SpatialCoverageField(_('Spatial coverage'))
    tags = fields.TagField(_('Tags'))
    private = fields.BooleanField(_('Private'))


class DatasetCreateForm(DatasetForm):
    organization = fields.PublishAsField(_('Publish as'))


class DatasetFullForm(DatasetForm):
    organization = fields.PublishAsField()
    extras = fields.ExtrasField(extras=Dataset.extras)


class ResourceForm(ModelForm):
    model_class = Resource

    title = fields.StringField(_('Title'), [validators.required()])
    description = fields.MarkdownField(_('Description'), [validators.required()])
    url = fields.UploadableURLField(_('URL'), [validators.required()], endpoint='storage.add_resource')
    format = fields.StringField(_('Format'), widget=widgets.FormatAutocompleter())
    checksum = fields.StringField(_('Checksum'))


class DatasetExtraForm(Form):
    key = fields.StringField(_('Key'), [validators.required()])
    value = fields.StringField(_('Value'), [validators.required()])
    old_key = fields.StringField(_('Old key'))
