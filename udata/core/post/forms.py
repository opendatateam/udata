# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from wtforms import validators

from udata.forms import UserModelForm, fields, widgets
from udata.i18n import lazy_gettext as _

from .models import Post, IMAGE_SIZES


__all__ = ('PostForm', )


class PostForm(UserModelForm):
    model_class = Post

    name = fields.StringField(_('Name'), [validators.required()])
    headline = fields.StringField(_('Headline'), widget=widgets.TextArea())
    content = fields.MarkdownField(_('Content'), [validators.required()])

    datasets = fields.DatasetListField(_('Associated datasets'))
    reuses = fields.ReuseListField(_('Associated reuses'))

    image = fields.ImageField(_('Image'), sizes=IMAGE_SIZES)
    # image_url = fields.UploadableURLField(_('Image URL'), description=_('The post thumbnail'),
    #     endpoint='storage.add_image')
    credit_to = fields.StringField(_('Image credits'))
    credit_url = fields.URLField(_('Credit URL'))

    tags = fields.TagField(_('Tags'))

    private = fields.BooleanField(_('Private'))
