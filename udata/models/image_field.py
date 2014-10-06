# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from mongoengine.errors import ValidationError
from mongoengine.fields import BaseField
from mongoengine.base.datastructures import BaseDict


log = logging.getLogger(__name__)


class ImageDict(BaseDict):
    @property
    def source(self):
        return self.get('source')

    @property
    def filename(self):
        return self.get('filename')

    def __unicode__(self):
        return self.get('source')

    __str__ = __unicode__


class ImageField(BaseField):
    def __set__(self, instance, value):
        if isinstance(value, basestring):
            value = {'source': value}
        return super(ImageField, self).__set__(instance, value)

    def __get__(self, instance, owner):
        value = super(ImageField, self).__get__(instance, owner)
        if value:
            return ImageDict(value, instance, self.name)
