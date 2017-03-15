# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from mongoengine.fields import URLField as MEURLField


class URLField(MEURLField):
    '''
    An URL field that automatically strips extra spaces
    '''
    def to_python(self, value):
        value = super(URLField, self).to_python(value)
        if value:
            return value.strip()
