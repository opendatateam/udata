# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, UserModelForm, fields, validators
from udata.i18n import lazy_gettext as _
from udata.models import Reuse, REUSE_TYPES

from .models import IMAGE_SIZES

__all__ = ('ReuseForm', 'ReuseCreateForm', 'AddDatasetToReuseForm')


class ReuseForm(UserModelForm):
    model_class = Reuse

    title = fields.StringField(_('Title'), [validators.required()])
    description = fields.MarkdownField(_('Description'), [validators.required()],
        description=_('The details about the reuse (build process, specifics, self-critics...).'))
    type = fields.SelectField(_('Type'), choices=REUSE_TYPES.items())
    url = fields.URLField(_('URL'), [validators.required()])
    image_url = fields.URLField(_('Image URL'),
        description=_('The reuse thumbnail'))
    image = fields.ImageField(_('Image'), sizes=IMAGE_SIZES)
    tags = fields.TagField(_('Tags'), description=_('Some taxonomy keywords'))
    datasets = fields.DatasetListField(_('Used datasets'))
    private = fields.BooleanField(_('Private'),
        description=_('Restrict the dataset visibility to you or your organization only.'))


class ReuseCreateForm(ReuseForm):
    organization = fields.PublishAsField(_('Publish as'))


class AddDatasetToReuseForm(Form):
    dataset = fields.StringField()
