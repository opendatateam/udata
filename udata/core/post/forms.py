# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import UserModelForm, fields, validators, widgets
from udata.i18n import lazy_gettext as _

from .models import Post


__all__ = ('PostForm', )


class PostForm(UserModelForm):
    model_class = Post

    name = fields.StringField(_('Name'), [validators.required()])
    content = fields.MarkdownField(_('Content'), [validators.required()])

    tags = fields.TagField(_('Tags'))

    private = fields.BooleanField(_('Private'))
