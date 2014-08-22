# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import wtforms_json; wtforms_json.init()
from flask.ext.mongoengine.wtf import model_form

from flask.ext.mongoengine.wtf.models import ModelForm as MEModelForm
from flask.ext.security import current_user
from flask.ext.wtf import Form

from udata import i18n

log = logging.getLogger(__name__)


class ModelForm(MEModelForm):
    def _get_translations(self):
        return i18n.domain.get_translations()


class UserModelFormMixin(object):
    user_field = 'owner'

    def validate(self):
        return super(UserModelFormMixin, self).validate() and current_user.is_authenticated()

    @property
    def errors(self):
        _errors = super(UserModelFormMixin, self).errors
        if not current_user.is_authenticated():
            _errors[self.user_field] = 'An authenticated user is required'
        return _errors

    def populate_obj(self, obj):
        if not getattr(obj, self.user_field):
            setattr(obj, self.user_field, current_user.to_dbref())
        super(UserModelFormMixin, self).populate_obj(obj)

    def save(self, **kwargs):
        self.data[self.user_field] = self.data.get(self.user_field, current_user.to_dbref())
        return super(UserModelFormMixin, self).save(**kwargs)

    @property
    def data(self):
        data = super(UserModelFormMixin, self).data
        data[self.user_field] = data.get(self.user_field, current_user.to_dbref())
        return data


class UserModelForm(UserModelFormMixin, ModelForm):
    pass


# Load core forms
from udata.core.user.forms import *
from udata.core.dataset.forms import *
from udata.core.reuse.forms import *
from udata.core.organization.forms import *
from udata.core.topic.forms import *
from udata.core.post.forms import *
