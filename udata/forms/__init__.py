import logging

import wtforms_json

from udata.flask_mongoengine.model_form import ModelForm as MEModelForm

wtforms_json.init()

from flask_wtf import FlaskForm

from udata import i18n

log = logging.getLogger(__name__)


class CommonFormMixin:
    def process(self, formdata=None, obj=None, data=None, extra_filters=None, **kwargs):
        """Wrap the process method to store the current object instance"""
        self._obj = obj
        super().process(formdata, obj, data, extra_filters=extra_filters, **kwargs)


class Form(CommonFormMixin, FlaskForm):
    pass


class ModelForm(CommonFormMixin, MEModelForm):
    model_class = None

    def _get_translations(self):
        return i18n.domain.get_translations()
