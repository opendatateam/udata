# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from mongoengine.errors import ValidationError
from mongoengine.fields import BaseField
from mongoengine.base.datastructures import BaseDict


log = logging.getLogger(__name__)


class FileDict(BaseDict):
    def __init__(self, dict_items, instance, name, fs=None):
        self.fs = fs
        super(FileDict, self).__init__(dict_items, instance, name)

    # @property
    # def fs(self):
    #     return self._instance.fs

    @property
    def source(self):
        return self.get('source')

    @property
    def filename(self):
        return self.get('filename')

    def save(self, wfs, filename=None):
        '''Save a Werkzeug FileStorage object'''
        filename = self.fs.save(wfs, filename)
        self['filename'] = filename
        return filename

    def url(self):
        return self.fs.url(self.get('filename'))

    def __unicode__(self):
        return self.url

    __str__ = __unicode__


class FileField(BaseField):
    def __init__(self, fs=None, *args, **kwargs):
        self.fs = fs
        super(FileField, self).__init__(*args, **kwargs)

    def __set__(self, instance, value):
        if isinstance(value, basestring):
            value = {'filename': value}
        return super(FileField, self).__set__(instance, value)

    def __get__(self, instance, owner):
        value = super(FileField, self).__get__(instance, owner)
        return FileDict(value or {}, instance, self.name)

    def to_mongo(self, value):
        return value or None


class ImageField(FileField):
    pass
