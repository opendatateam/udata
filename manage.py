#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
uData development Launcher
'''
from __future__ import unicode_literals

import os

from udata.commands import cli

if __name__ == '__main__':
    # Run the application in debug mode
    os.environ['FLASK_DEBUG'] = 'true'
    cli(settings='udata.settings.Debug')
