# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import re

from werkzeug.exceptions import HTTPException
from udata import entrypoints
from udata.core.storages.api import UploadProgress
from .auth import PermissionDenied


log = logging.getLogger(__name__)

RE_DSN = re.compile(
    r'(?P<scheme>https?)://(?P<client_id>[0-9a-f]+):[0-9a-f]+'
    '@(?P<domain>.+)/(?P<site_id>\d+)')

# Controlled exceptions that Sentry should ignore
IGNORED_EXCEPTIONS = HTTPException, PermissionDenied, UploadProgress


def public_dsn(dsn):
    '''Transform a standard Sentry DSN into a public one'''
    m = RE_DSN.match(dsn)
    if not m:
        log.error('Unable to parse Sentry DSN')
    public = '{scheme}://{client_id}@{domain}/{site_id}'.format(
        **m.groupdict())
    return public


def init_app(app):
    if 'SENTRY_DSN' in app.config:
        try:
            from raven.contrib.celery import (
                register_signal, register_logger_signal
            )
            from raven.contrib.flask import Sentry
        except ImportError:
            log.error('raven[flask] is required to use sentry')
            return

        sentry = Sentry()
        tags = app.config['SENTRY_TAGS'] = app.config.get('SENTRY_TAGS', {})

        app.config.setdefault('SENTRY_USER_ATTRS',
                              ['slug', 'email', 'fullname'])
        app.config.setdefault('SENTRY_LOGGING', 'WARNING')

        log_level_name = app.config.get('SENTRY_LOGGING')
        if log_level_name:
            log_level = getattr(logging, log_level_name.upper())
            if log_level:
                sentry.logging = True
                sentry.level = log_level

        # Do not send HTTPExceptions
        exceptions = set(app.config.get('RAVEN_IGNORE_EXCEPTIONS', []))
        for exception in IGNORED_EXCEPTIONS:
            exceptions.add(exception)
        app.config['RAVEN_IGNORE_EXCEPTIONS'] = list(exceptions)

        app.config['SENTRY_PUBLIC_DSN'] = public_dsn(app.config['SENTRY_DSN'])

        # Versions Management: uData and plugins versions as tags.
        for dist in entrypoints.get_plugins_dists(app):
            if dist.version:
                tags[dist.project_name] = dist.version

        sentry.init_app(app)

        # register a custom filter to filter out duplicate logs
        register_logger_signal(sentry.client, loglevel=sentry.level)

        # hook into the Celery error handler
        register_signal(sentry.client)
