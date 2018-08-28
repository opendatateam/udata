# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import ModelForm, fields, validators, widgets
from udata.i18n import lazy_gettext as _

from .models import Post, IMAGE_SIZES


__all__ = ('PostForm', )


class PostForm(ModelForm):
    model_class = Post

    owner = fields.CurrentUserField()

    name = fields.StringField(_('Name'), [validators.required()])
    headline = fields.StringField(_('Headline'), widget=widgets.TextArea())
    content = fields.MarkdownField(_('Content'), [validators.required()])

    datasets = fields.DatasetListField(_('Associated datasets'))
    reuses = fields.ReuseListField(_('Associated reuses'))

    image = fields.ImageField(_('Image'), sizes=IMAGE_SIZES)
    credit_to = fields.StringField(_('Image credits'))
    credit_url = fields.URLField(_('Credit URL'))

    tags = fields.TagField(_('Tags'))
