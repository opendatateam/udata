# -*- coding: utf-8 -*-
'''
uData customizations for Data.gouv.fr
'''
from __future__ import unicode_literals

__version__ = '0.9.0.dev'
__description__ = 'uData customizations for Data.gouv.fr'


def init_app(app):
    from . import harvesters  # noqa: needed for registration
