import logging
import pkg_resources
import re
import warnings

from werkzeug.exceptions import HTTPException
from udata import entrypoints
from udata.core.storages.api import UploadProgress
from .auth import PermissionDenied


log = logging.getLogger(__name__)

RE_DSN = re.compile(
    r'(?P<scheme>https?)://(?P<client_id>[0-9a-f]+)(?::(?P<secret>[0-9a-f]+))?'
    r'@(?P<domain>.+)/(?P<site_id>\d+)')

SECRET_DSN_DEPRECATED_MSG = 'DSN with secret is deprecated, use a public DSN instead'
ERROR_PARSE_DSN_MSG = 'Unable to parse Sentry DSN'

# Controlled exceptions that Sentry should ignore
IGNORED_EXCEPTIONS = HTTPException, PermissionDenied, UploadProgress

def public_dsn(dsn):
    '''Check if DSN is public or raise a warning and turn it into a public one'''
    m = RE_DSN.match(dsn)
    if not m:
        log.error(ERROR_PARSE_DSN_MSG)
        raise ValueError(ERROR_PARSE_DSN_MSG)

    if not m["secret"]:
        return dsn

    log.warning(SECRET_DSN_DEPRECATED_MSG)
    warnings.warn(SECRET_DSN_DEPRECATED_MSG, category=DeprecationWarning)

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

        app.config['SENTRY_PUBLIC_DSN'] = public_dsn(app.config['SENTRY_DSN'])

        # Do not send HTTPExceptions
        exceptions = set(app.config['SENTRY_IGNORE_EXCEPTIONS'])
        for exception in IGNORED_EXCEPTIONS:
            exceptions.add(exception)

        sentry_sdk.init(
            dsn=app.config['SENTRY_PUBLIC_DSN'],
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
