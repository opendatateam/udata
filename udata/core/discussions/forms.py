# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import ModelForm, Form, fields, validators
from udata.i18n import lazy_gettext as _

from .models import Discussion

__all__ = ('DiscussionCreateForm', 'DiscussionCommentForm')


class DiscussionCreateForm(ModelForm):
    model_class = Discussion

    title = fields.StringField(_('Title'), [validators.required()])
    comment = fields.StringField(_('Comment'), [validators.required()])
    subject = fields.ModelField(_('Subject'), [validators.required()])
    extras = fields.ExtrasField(extras=Discussion.extras)


class DiscussionCommentForm(Form):
    comment = fields.StringField(_('Comment'), [validators.required()])
    close = fields.BooleanField(default=False)
