# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask.ext.wtf import Form
from wtforms import validators

from udata.auth import current_user
from udata.forms import ModelForm, fields
from udata.i18n import lazy_gettext as _
from udata.models import Reuse, REUSE_TYPES

from .models import IMAGE_SIZES

__all__ = ('ReuseForm', 'ReuseCreateForm', 'AddDatasetToReuseForm')


def check_url_does_not_exists(form, field):
    '''Ensure a reuse URL is not yet registered'''
    if field.data != field.object_data and Reuse.url_exists(field.data):
        raise validators.ValidationError(_('This URL is already registered'))


class ReuseForm(ModelForm):
    model_class = Reuse

    title = fields.StringField(_('Title'), [validators.required()])
    description = fields.MarkdownField(_('Description'), [validators.required()],
        description=_('The details about the reuse (build process, specifics, self-critics...).'))
    type = fields.SelectField(_('Type'), choices=REUSE_TYPES.items())
    url = fields.URLField(_('URL'), [validators.required(), check_url_does_not_exists])
    # image_url = fields.URLField(_('Image URL'),
    #     description=_('The reuse thumbnail'))
    image = fields.ImageField(_('Image'), sizes=IMAGE_SIZES, placeholder='reuse')
    tags = fields.TagField(_('Tags'), description=_('Some taxonomy keywords'))
    datasets = fields.DatasetListField(_('Used datasets'))
    private = fields.BooleanField(_('Private'),
        description=_('Restrict the dataset visibility to you or your organization only.'))


class ReuseCreateForm(ReuseForm):
    organization = fields.PublishAsField(_('Publish as'))

    def save(self, commit=True, **kwargs):
        reuse = super(ReuseCreateForm, self).save(commit=False, **kwargs)
        if not reuse.organization:
            reuse.owner = current_user._get_current_object()

        if commit:
            reuse.save()

        return reuse


class AddDatasetToReuseForm(Form):
    dataset = fields.StringField()
