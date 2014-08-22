# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import PeriodicTask


class PeriodicTaskForm(ModelForm):
    model_class = PeriodicTask

    name = fields.StringField(_('Name'), [validators.required()])
    description = fields.StringField(_('Description'))
    task = fields.StringField(_('Tasks'))

