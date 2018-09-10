# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from udata.entrypoints import get_enabled, EntrypointError


def get(app, name):
    '''Get a backend given its name'''
    backend = get_all(app).get(name)
    if not backend:
        msg = 'Harvest backend "{0}" is not registered'.format(name)
        raise EntrypointError(msg)
    return backend


def get_all(app):
    return get_enabled('udata.harvesters', app)


from .base import BaseBackend, HarvestFilter, HarvestFeature  # flake8: noqa
