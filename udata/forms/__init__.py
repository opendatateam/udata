# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import wtforms_json
wtforms_json.init()
from flask_mongoengine.wtf import model_form  # noqa

from flask_mongoengine.wtf.models import ModelForm as MEModelForm  # noqa
from flask_wtf import Form as WTForm  # noqa

from udata import i18n  # noqa

log = logging.getLogger(__name__)


class CommonFormMixin(object):
    def process(self, formdata=None, obj=None, data=None, **kwargs):
        '''Wrap the process method to store the current object instance'''
        self._obj = obj
        super(CommonFormMixin, self).process(formdata, obj, data, **kwargs)


class Form(CommonFormMixin, WTForm):
    pass


class ModelForm(CommonFormMixin, MEModelForm):
    def _get_translations(self):
        return i18n.domain.get_translations()
