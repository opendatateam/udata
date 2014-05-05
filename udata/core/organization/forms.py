# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _
from udata.models import Organization

__all__ = ('OrganizationForm', 'OrganizationMemberForm')


class OrganizationForm(ModelForm):
    model_class = Organization

    name = fields.StringField(_('Name'), [validators.required()])
    description = fields.MarkdownField(_('Description'), [validators.required()])
    url = fields.URLField(_('URL'))
    image_url = fields.URLField(_('Image URL'))


class OrganizationMemberForm(ModelForm):
    model_class = Organization

    pk = fields.UserField(validators=[validators.required()])
    value = fields.StringField(default='editor')
