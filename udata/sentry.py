import logging
import pkg_resources
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

# TODO: check if public_dsn is still needed (no secret anymore) ?

def public_dsn(dsn):
    '''Transform a standard Sentry DSN into a public one'''
    m = RE_DSN.match(dsn)
    if not m:
        log.error('Unable to parse Sentry DSN')
    public = '{scheme}://{client_id}@{domain}/{site_id}'.format(
        **m.groupdict())
    return public


def init_app(app):
    if app.config['SENTRY_DSN']:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.flask import FlaskIntegration
            from sentry_sdk.integrations.celery import CeleryIntegration
        except ImportError:
            log.error('sentry-sdk is required to use Sentry')
            return

        sentry_public_dsn = public_dsn(app.config['SENTRY_DSN'])

        # Do not send HTTPExceptions
        exceptions = set(app.config['SENTRY_IGNORE_EXCEPTIONS'])
        for exception in IGNORED_EXCEPTIONS:
            exceptions.add(exception)

        sentry_sdk.init(
            dsn=sentry_public_dsn,
            integrations=[FlaskIntegration(), CeleryIntegration()],
            ignore_errors=list(exceptions)
        )

        # Set log level
        log_level_name = app.config['SENTRY_LOGGING']
        if log_level_name:
            log_level = getattr(logging, log_level_name.upper())
            sentry_sdk.set_level(log_level)

        # Set sentry tags
        tags = app.config['SENTRY_TAGS']
        for tag_key in tags:
            sentry_sdk.set_tag(tag_key, tags[tag_key])
        # Versions Management: uData and plugins versions as tags.
        for dist in entrypoints.get_plugins_dists(app):
            if dist.version:
                sentry_sdk.set_tag(dist.project_name, dist.version)
        # Do not forget udata itself
        sentry_sdk.set_tag('udata', pkg_resources.get_distribution('udata').version)
