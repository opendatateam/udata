# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from flask import current_app

from udata.commands import manager, white


log = logging.getLogger(__name__)


@manager.command
def info():
    '''Display some details about the local configuration'''
    if hasattr(current_app, 'settings_file'):
        log.info('Loaded configuration from %s', current_app.settings_file)

    log.info('Current configuration')
    for key in sorted(current_app.config):
        print('{0}: {1}'.format(white(key), current_app.config[key]))
