# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)


def init_app(app):
    if 'SENTRY_DSN' in app.config:
        try:
            from raven.contrib.flask import Sentry
        except:
            log.error('raven[flask] is required to use sentry')
            return

        sentry = Sentry()

        app.config.setdefault('SENTRY_USER_ATTRS', ['slug', 'email', 'fullname'])
        app.config.setdefault('SENTRY_LOGGING',  'WARNING')

        log_level_name = app.config.get('SENTRY_LOGGING')
        if log_level_name:
            log_level = getattr(logging, log_level_name.upper())
            if log_level:
                sentry.logging = True
                sentry.level = log_level

        # Do not send HTTPExceptions
        exceptions = app.config.get('RAVEN_IGNORE_EXCEPTIONS', [])
        if HTTPException not in exceptions:
            exceptions.append(HTTPException)
        app.config['RAVEN_IGNORE_EXCEPTIONS'] = exceptions

        sentry.init_app(app)
