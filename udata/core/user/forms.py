# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import ModelForm, fields, validators, widgets
from udata.i18n import lazy_gettext as _
from udata.models import User


__all__ = ('UserProfileForm',)


class UserProfileForm(ModelForm):
    model_class = User

    first_name = fields.StringField(_('First name'), [validators.required()])
    last_name = fields.StringField(_('Last name'), [validators.required()])
    avatar_url = fields.URLField(_('Avatar URL'))
    website = fields.URLField(_('Website'))
    about = fields.MarkdownField(_('About'))
