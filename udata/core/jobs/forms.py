# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import PeriodicTask


class CrontabForm(ModelForm):
    model_class = PeriodicTask.Crontab

    minute = fields.StringField(default='*')
    hour = fields.StringField(default='*')
    day_of_week = fields.StringField(default='*')
    day_of_month = fields.StringField(default='*')
    month_of_year = fields.StringField(default='*')


class IntervalForm(ModelForm):
    model_class = PeriodicTask.Interval

    every = fields.IntegerField(validators=[validators.NumberRange(min=0)])
    period = fields.StringField()


class PeriodicTaskForm(ModelForm):
    model_class = PeriodicTask

    name = fields.StringField(_('Name'), [validators.required()])
    description = fields.StringField(_('Description'))
    task = fields.StringField(_('Tasks'))


class CrontabTaskForm(PeriodicTaskForm):
    crontab = fields.FormField(CrontabForm)


class IntervalTaskForm(PeriodicTaskForm):
    interval = fields.FormField(IntervalForm)
