# -*- coding: utf-8 -*-
'''
uData Data.gouv.fr customization
'''
from __future__ import unicode_literals

__version__ = '0.1.0.dev'
__description__ = 'uData Data.gouv.fr customizations'


def init_app(app):
    from . import harvesters  # noqa: needed for registration
