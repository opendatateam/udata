# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

backends = {}

def register(cls):
    '''Register a backend class'''
    if hasattr(cls, 'name'):
        backends[cls.name] = cls
    return cls


def get(name):
    '''Get a backend given its name'''
    return backends.get(name)


def get_all():
    return backends


from .base import BaseHarvester
from .ods import OdsHarvester