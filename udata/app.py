import datetime
import importlib
import logging
import os
import types
from os.path import abspath, dirname, exists, isfile, join

import bson
from flask import Blueprint as BaseBlueprint
from flask import Flask, abort, g, json, make_response, send_from_directory
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from speaklater import is_lazy_string
from werkzeug.middleware.proxy_fix import ProxyFix

from udata import cors, entrypoints

APP_NAME = __name__.split(".")[0]
ROOT_DIR = abspath(join(dirname(__file__)))

log = logging.getLogger(__name__)

cache = Cache()
csrf = CSRFProtect()


def send_static(directory, filename, cache_timeout):
    out = send_from_directory(directory, filename, cache_timeout=cache_timeout)
    response = make_response(out)
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


class UDataApp(Flask):
    debug_log_format = "[%(levelname)s][%(name)s:%(lineno)d] %(message)s"

    # Keep track of static dirs given as register_blueprint argument
    static_prefixes = {}

    def send_static_file(self, filename):
        """
        Override default static handling:
        - raises 404 if not debug
        - handle static aliases
        """
        if not self.debug:
            self.logger.error("Static files are only served in debug")
            abort(404)

        cache_timeout = self.get_send_file_max_age(filename)

        # Default behavior
        if isfile(join(self.static_folder, filename)):
            return send_static(self.static_folder, filename, cache_timeout=cache_timeout)

        # Handle aliases
        for prefix, directory in self.config.get("STATIC_DIRS", tuple()):
            if filename.startswith(prefix):
                real_filename = filename[len(prefix) :]
                if real_filename.startswith("/"):
                    real_filename = real_filename[1:]
                if isfile(join(directory, real_filename)):
                    return send_static(directory, real_filename, cache_timeout=cache_timeout)
        abort(404)

    def handle_http_exception(self, e):
        # Make exception/HTTPError available for context processors
        if "error" not in g:
            g.error = e
        return super(UDataApp, self).handle_http_exception(e)

    def register_blueprint(self, blueprint, **kwargs):
        if blueprint.name in self.blueprints:
            # TODO: remove this warning and let Flask return a ValueError once
            # we can set a custom blueprint name in Flask-storage
            self.logger.warning("Blueprint already loaded")
            return self.blueprints[blueprint.name]

        if blueprint.has_static_folder and "url_prefix" in kwargs:
            self.static_prefixes[blueprint.name] = kwargs["url_prefix"]
        return super(UDataApp, self).register_blueprint(blueprint, **kwargs)


class Blueprint(BaseBlueprint):
    """A blueprint allowing to decorate class too"""

    def route(self, rule, **options):
        def wrapper(func_or_cls):
            endpoint = str(options.pop("endpoint", func_or_cls.__name__))
            if isinstance(func_or_cls, types.FunctionType):
                self.add_url_rule(rule, endpoint, func_or_cls, **options)
            else:
                self.add_url_rule(rule, view_func=func_or_cls.as_view(endpoint), **options)
            return func_or_cls

        return wrapper


class UDataJsonEncoder(json.JSONEncoder):
    """
    A JSONEncoder subclass to encode unsupported types:

        - ObjectId
        - datetime
        - lazy strings

    Handle special serialize() method and _data attribute.
    Ensure an app context is always present.
    """

    def default(self, obj):
        if is_lazy_string(obj):
            return str(obj)
        elif isinstance(obj, bson.objectid.ObjectId):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif hasattr(obj, "serialize"):
            return obj.serialize()
        # Serialize Raw data for Document and EmbeddedDocument.
        elif hasattr(obj, "_data"):
            return obj._data
        return super(UDataJsonEncoder, self).default(obj)


# These loggers are very verbose
# We need to put them in WARNING level
# even if the main level is INFO or DEBUG
VERBOSE_LOGGERS = ("requests",)


def init_logging(app):
    logging.captureWarnings(True)  # Display warnings
    debug = app.debug or app.config.get("TESTING")
    log_level = logging.DEBUG if debug else logging.WARNING
    app.logger.setLevel(log_level)
    for name in entrypoints.get_roots():  # Entrypoints loggers
        logging.getLogger(name).setLevel(log_level)
    for logger in VERBOSE_LOGGERS:
        logging.getLogger(logger).setLevel(logging.WARNING)
    return app


def create_app(config="udata.settings.Defaults", override=None, init_logging=init_logging):
    """Factory for a minimal application"""
    app = UDataApp(APP_NAME)
    app.config.from_object(config)

    settings = os.environ.get("UDATA_SETTINGS", join(os.getcwd(), "udata.cfg"))
    if exists(settings):
        app.settings_file = settings  # Keep track of loaded settings for diagnostic
        app.config.from_pyfile(settings)

    if override:
        app.config.from_object(override)

    # Loads defaults from plugins
    for pkg in entrypoints.get_roots(app):
        if pkg == "udata":
            continue  # Defaults are already loaded
        module = "{}.settings".format(pkg)
        try:
            settings = importlib.import_module(module)
        except ImportError:
            continue
        for key, default in settings.__dict__.items():
            if key.startswith("__"):
                continue
            app.config.setdefault(key, default)

    app.json_encoder = UDataJsonEncoder

    # `ujson` doesn't support `cls` parameter https://github.com/ultrajson/ultrajson/issues/124
    app.config["RESTX_JSON"] = {"cls": UDataJsonEncoder}

    app.debug = app.config["DEBUG"] and not app.config["TESTING"]

    app.wsgi_app = ProxyFix(app.wsgi_app)

    init_logging(app)
    register_extensions(app)

    return app


def standalone(app):
    """Factory for an all in one application"""
    from udata import api, core, frontend

    core.init_app(app)
    frontend.init_app(app)
    api.init_app(app)

    register_features(app)

    return app


def register_extensions(app):
    from udata import (
        auth,
        i18n,
        mail,
        models,
        mongo,
        notifications,  # noqa
        routing,
        search,
        sentry,
        tasks,
    )

    cors.init_app(app)
    tasks.init_app(app)
    i18n.init_app(app)
    mongo.init_app(app)
    models.init_app(app)
    routing.init_app(app)
    auth.init_app(app)
    cache.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    search.init_app(app)
    sentry.init_app(app)
    return app


def register_features(app):
    from udata.features import notifications

    notifications.init_app(app)

    for ep in entrypoints.get_enabled("udata.plugins", app).values():
        ep.init_app(app)
