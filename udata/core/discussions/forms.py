# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import ModelForm, Form, fields, validators
from udata.i18n import lazy_gettext as _

from .models import Discussion

__all__ = ('DiscussionCreateForm', 'DiscussionCommentForm')


class DiscussionCreateForm(ModelForm):
    model_class = Discussion

    title = fields.StringField(_('Title'), [validators.DataRequired()])
    comment = fields.StringField(_('Comment'), [validators.DataRequired()])
    subject = fields.ModelField(_('Subject'), [validators.DataRequired()])
    extras = fields.ExtrasField()


class DiscussionCommentForm(Form):
    comment = fields.StringField(_('Comment'), [validators.DataRequired()])
    close = fields.BooleanField(default=False)
