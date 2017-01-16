# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import Issue

__all__ = ('IssueCreateForm', 'IssueCommentForm')


class IssueCreateForm(ModelForm):
    model_class = Issue

    title = fields.StringField(_('Title'), [validators.required()])
    comment = fields.StringField(_('Comment'), [validators.required()])
    subject = fields.ModelField(_('Subject'), [validators.required()])


class IssueCommentForm(Form):
    comment = fields.StringField(_('Comment'), [validators.required()])
    close = fields.BooleanField(default=False)
