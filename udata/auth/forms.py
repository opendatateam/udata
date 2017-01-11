# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask_security.forms import RegisterForm
from udata.forms import fields
from udata.forms import validators


class ExtendedRegisterForm(RegisterForm):
    first_name = fields.StringField(
        'First Name', [validators.Required('First name is required')])
    last_name = fields.StringField(
        'Last Name', [validators.Required('Last name is required')])
