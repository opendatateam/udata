# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask.ext.mongoengine.wtf.models import ModelForm as MEModelForm
from flask.ext.security import current_user
from flask.ext.wtf import Form

from udata import i18n

log = logging.getLogger(__name__)


class ModelForm(MEModelForm):
    def _get_translations(self):
        return i18n.domain.get_translations()


class UserModelForm(ModelForm):
    user_field = 'owner'

    def validate(self):
        return super(UserModelForm, self).validate() and current_user.is_authenticated()

    @property
    def errors(self):
        _errors = super(UserModelForm, self).errors
        if not current_user.is_authenticated():
            _errors[self.user_field] = 'An authenticated user is required'
        return _errors

    def populate_obj(self, obj):
        super(UserModelForm, self).populate_obj(obj)
        if not getattr(obj, self.user_field):
            setattr(obj, self.user_field, current_user.to_dbref())

    def save(self, **kwargs):
        self.data[self.user_field] = self.data.get(self.user_field, current_user.to_dbref())
        return super(UserModelForm, self).save(**kwargs)

    @property
    def data(self):
        data = super(UserModelForm, self).data
        data[self.user_field] = data.get(self.user_field, current_user.to_dbref())
        return data


# Load core forms
from udata.core.user.forms import *
from udata.core.dataset.forms import *
from udata.core.reuse.forms import *
from udata.core.organization.forms import *
from udata.core.topic.forms import *
from udata.core.post.forms import *
