# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask_security.forms import RegisterForm
from udata.forms import fields
from udata.forms import validators
from udata.i18n import lazy_gettext as _


class ExtendedRegisterForm(RegisterForm):
    first_name = fields.StringField(
        _('First name'), [validators.Required(_('First name is required'))])
    last_name = fields.StringField(
        _('Last name'), [validators.Required(_('Last name is required'))])
