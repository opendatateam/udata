# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import pkg_resources

from udata.entrypoints import get_all as get_all_entrypoints


def get(name):
    '''Get a backend given its name'''
    return get_all().get(name)


def get_all():
    return get_all_entrypoints('udata.harvesters')


from .base import BaseBackend  # flake8: noqa
