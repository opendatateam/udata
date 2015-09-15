# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _
from udata.models import Reuse, REUSE_TYPES

from .models import IMAGE_SIZES

__all__ = ('ReuseForm', )


def check_url_does_not_exists(form, field):
    '''Ensure a reuse URL is not yet registered'''
    if field.data != field.object_data and Reuse.url_exists(field.data):
        raise validators.ValidationError(_('This URL is already registered'))


class ReuseForm(ModelForm):
    model_class = Reuse

    title = fields.StringField(_('Title'), [validators.required()])
    description = fields.MarkdownField(
        _('Description'), [validators.required()],
        description=_('The details about the reuse (build process, specifics, '
                      'self-critics...).'))
    type = fields.SelectField(_('Type'), choices=REUSE_TYPES.items())
    url = fields.URLField(
        _('URL'), [validators.required(), check_url_does_not_exists])
    image = fields.ImageField(
        _('Image'), sizes=IMAGE_SIZES, placeholder='reuse')
    tags = fields.TagField(_('Tags'), description=_('Some taxonomy keywords'))
    datasets = fields.DatasetListField(_('Used datasets'))
    private = fields.BooleanField(
        _('Private'),
        description=_('Restrict the dataset visibility to you or '
                      'your organization only.'))

    owner = fields.CurrentUserField()
    organization = fields.PublishAsField(_('Publish as'))
