# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, ModelForm, UserModelForm, fields, validators
from udata.i18n import lazy_gettext as _
from udata.models import Organization, MembershipRequest

__all__ = ('OrganizationForm', 'OrganizationMemberForm', 'OrganizationExtraForm', 'MembershipRequestForm')


class OrganizationForm(ModelForm):
    model_class = Organization

    name = fields.StringField(_('Name'), [validators.required()])
    description = fields.MarkdownField(_('Description'), [validators.required()])
    url = fields.URLField(_('URL'))
    image_url = fields.URLField(_('Image URL'))


class OrganizationMemberForm(ModelForm):
    model_class = Organization

    pk = fields.StringField(validators=[validators.required()])
    value = fields.StringField(default='editor')


class OrganizationExtraForm(Form):
    key = fields.StringField(_('Key'), [validators.required()])
    value = fields.StringField(_('Value'), [validators.required()])
    old_key = fields.StringField(_('Old key'))


class MembershipRequestForm(UserModelForm):
    model_class = MembershipRequest
    user_field = 'user'

    comment = fields.StringField(_('Comment'), [validators.required()])
