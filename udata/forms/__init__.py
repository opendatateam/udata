# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import wtforms_json
wtforms_json.init()
from flask.ext.mongoengine.wtf import model_form

from flask.ext.mongoengine.wtf.models import ModelForm as MEModelForm
from flask.ext.wtf import Form

from udata import i18n

log = logging.getLogger(__name__)


class ModelForm(MEModelForm):
    def _get_translations(self):
        return i18n.domain.get_translations()
