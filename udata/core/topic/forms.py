# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from wtforms import validators

from udata.forms import UserModelForm, fields
from udata.i18n import lazy_gettext as _

from .models import Topic


__all__ = ('TopicForm', )


class TopicForm(UserModelForm):
    model_class = Topic

    name = fields.StringField(_('Name'), [validators.required()])
    description = fields.MarkdownField(_('Description'), [validators.required()])

    datasets = fields.DatasetListField(_('Associated datasets'))
    reuses = fields.ReuseListField(_('Associated reuses'))

    tags = fields.TagField(_('Tags'), [validators.required()])
    private = fields.BooleanField(_('Private'))
