#!/usr/bin/env python

'''
uData development Launcher
'''

import os

from udata.commands import cli

if __name__ == '__main__':
    # Run the application in debug mode
    os.environ['FLASK_DEBUG'] = 'true'
    cli(settings='udata.settings.Debug')
