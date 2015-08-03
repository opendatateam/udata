# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

_registered_backends = {}


def register(cls):
    '''Register a backend class'''
    if hasattr(cls, 'name'):
        _registered_backends[cls.name] = cls
    return cls


def get(name):
    '''Get a backend given its name'''
    return _registered_backends.get(name)


def get_all():
    return _registered_backends


from .base import BaseBackend
from .dummy import DummyBackend
from ..harvesters import OdsHarvester