# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.forms import ModelForm, fields, validators
from udata.i18n import lazy_gettext as _

from .models import Site

__all__ = ('SiteConfigForm', )


class SiteConfigForm(ModelForm):
    model_class = Site

    title = fields.StringField(_('Title'), [validators.required()])
    keywords = fields.TagField(_('Tags'), description=_('Some SEO keywords'))
    feed_size = fields.IntegerField(
        _('Feed size'), description=_('Number of elements in feeds'))
