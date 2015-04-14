# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app
from wtforms import validators

from udata.forms import ModelForm, fields
from udata.i18n import lazy_gettext as _
from udata.models import User

from .models import AVATAR_SIZES


__all__ = ('UserProfileForm', 'UserSettingsForm', 'UserAPIKeyForm', 'UserNotificationsForm')


class UserProfileForm(ModelForm):
    model_class = User

    first_name = fields.StringField(_('First name'), [validators.required()])
    last_name = fields.StringField(_('Last name'), [validators.required()])
    # avatar_url = fields.URLField(_('Avatar URL'))
    avatar = fields.ImageField(_('Avatar'), sizes=AVATAR_SIZES)
    website = fields.URLField(_('Website'))
    about = fields.MarkdownField(_('About'))


class UserSettingsForm(ModelForm):
    model_class = User

    prefered_language = fields.SelectField(_('Prefered language'),
        choices=lambda: current_app.config['LANGUAGES'].items())


class UserAPIKeyForm(ModelForm):
    model_class = User

    action = fields.SelectField(choices=(('generate',''), ('clear', '')), validators=[validators.required()])


class UserNotificationsForm(ModelForm):
    model_class = User
