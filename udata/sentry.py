import logging

from werkzeug.exceptions import HTTPException

from udata import entrypoints
from udata.core.storages.api import UploadProgress

from .app import UDataApp
from .auth import PermissionDenied
from .frontend import package_version

log = logging.getLogger(__name__)


# Controlled exceptions that Sentry should ignore
IGNORED_EXCEPTIONS = HTTPException, PermissionDenied, UploadProgress


def init_app(app: UDataApp):
    if app.config["SENTRY_DSN"]:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.celery import CeleryIntegration
            from sentry_sdk.integrations.flask import FlaskIntegration
        except ImportError:
            log.error("sentry-sdk is required to use Sentry")
            return

        # Do not send HTTPExceptions
        exceptions = set(app.config["SENTRY_IGNORE_EXCEPTIONS"])
        for exception in IGNORED_EXCEPTIONS:
            exceptions.add(exception)

        sentry_sdk.init(
            dsn=app.config["SENTRY_DSN"],
            integrations=[FlaskIntegration(), CeleryIntegration()],
            ignore_errors=list(exceptions),
            release=f"udata@{package_version('udata')}",
            environment=app.config.get("SITE_ID", None),
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            # Sentry recommends adjusting this value in production.
            traces_sample_rate=app.config.get("SENTRY_SAMPLE_RATE", None),
            profiles_sample_rate=app.config.get("SENTRY_SAMPLE_RATE", None),
        )

        # Set log level
        log_level_name = app.config["SENTRY_LOGGING"]
        if log_level_name:
            log_level = getattr(logging, log_level_name.upper())
            sentry_sdk.set_level(log_level)

        # Versions Management: uData and plugins versions as tags.
        for dist in entrypoints.get_plugins_dists(app):
            if dist.version:
                sentry_sdk.set_tag(dist.project_name, dist.version)
        # Do not forget udata itself (is that necessary since we already have the release?)
        sentry_sdk.set_tag("udata", package_version("udata"))
