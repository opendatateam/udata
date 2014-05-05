# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import UserModelForm, fields, validators, widgets
from udata.i18n import lazy_gettext as _

from .models import Topic


__all__ = ('TopicForm', )


class TopicForm(UserModelForm):
    model_class = Topic

    name = fields.StringField(_('Name'), [validators.required()])
    description = fields.MarkdownField(_('Description'), [validators.required()])
    query = fields.StringField(_('Query'), [validators.required()])

    tags = fields.TagField(_('Tags'))
    private = fields.BooleanField(_('Private'))
