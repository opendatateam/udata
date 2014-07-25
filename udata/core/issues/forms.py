# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import Form, fields, validators
from udata.i18n import lazy_gettext as _

from .models import ISSUE_TYPES

__all__ = ('IssueCreateForm', 'IssueCommentForm')


class IssueCreateForm(Form):
    comment = fields.StringField(_('Comment'), [validators.required()])
    type = fields.SelectField(_('Type'), [validators.required()], choices=ISSUE_TYPES.items())


class IssueCommentForm(Form):
    comment = fields.StringField(_('Comment'), [validators.required()])
    close = fields.BooleanField(default=False)
