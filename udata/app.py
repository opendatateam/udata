# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import bson
import datetime
import logging
import os

from os.path import abspath, join, dirname, isfile, exists

from flask import Flask, abort, send_from_directory, json
from flask.ext.cache import Cache


APP_NAME = __name__.split('.')[0]
ROOT_DIR = abspath(join(dirname(__file__)))

log = logging.getLogger(__name__)

cache = Cache()


class UDataApp(Flask):
    def send_static_file(self, filename):
        '''
        Override default static handling:
        - raises 404 if not debug
        - handle static aliases
        '''
        if not self.debug:
            self.logger.error('not debug')
            abort(404)

        cache_timeout = self.get_send_file_max_age(filename)

        # Default behavior
        if isfile(join(self.static_folder, filename)):
            return send_from_directory(self.static_folder, filename, cache_timeout=cache_timeout)

        # Handle aliases
        for prefix, directory in self.config.get('STATIC_DIRS', tuple()):
            if filename.startswith(prefix):
                real_filename = filename[len(prefix):]
                if real_filename.startswith('/'):
                    real_filename = real_filename[1:]
                if isfile(join(directory, real_filename)):
                    return send_from_directory(directory, real_filename, cache_timeout=cache_timeout)
        abort(404)


class UDataJsonEncoder(json.JSONEncoder):
    """A C{json.JSONEncoder} subclass to encode documents that have fields of
    type C{bson.objectid.ObjectId}, C{datetime.datetime}
    """
    def default(self, obj):
        if isinstance(obj, bson.objectid.ObjectId):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super(UDataJsonEncoder, self).default(obj)


def create_app(config='udata.settings.Defaults'):
    '''Factory for a minimal application'''
    app = UDataApp(APP_NAME)
    app.config.from_object(config)
    app.config.from_envvar('UDATA_SETTINGS', silent=True)
    custom_settings = join(os.getcwd(), 'udata.cfg')
    if exists(custom_settings):
        app.config.from_pyfile(custom_settings)

    app.json_encoder = UDataJsonEncoder

    app.debug = app.config['DEBUG'] and not app.config['TESTING']

    init_logging(app)
    register_extensions(app)

    return app


def standalone(app):
    '''Factory for an all in one application'''
    from udata import admin, api, core, frontend

    core.init_app(app)
    frontend.init_app(app)
    api.init_app(app)
    admin.init_app(app)

    from udata import ext
    ext.init_app(app)
    return app


def init_logging(app):
    logging.getLogger('').addHandler(logging.NullHandler())
    log_level = logging.DEBUG if app.debug else logging.WARNING
    app.logger.setLevel(log_level)
    # logging.getLogger('udata').setLevel(log_level)
    logging.getLogger('werkzeug').setLevel(log_level)
    logging.getLogger('celery.task').setLevel(log_level)
    loggers = [
        logging.getLogger('elasticsearch'),
        logging.getLogger('requests')
    ]
    for name in app.config['PLUGINS']:
        logging.getLogger('udata_{0}'.format(name)).setLevel(log_level)
    for logger in loggers:
        logger.setLevel(logging.WARNING)
    return app


def register_extensions(app):
    from udata import models, routing, tasks, mail, i18n, auth
    i18n.init_app(app)
    models.init_app(app)
    routing.init_app(app)
    auth.init_app(app)
    cache.init_app(app)
    tasks.init_app(app)
    mail.init_app(app)

    from udata import search
    search.init_app(app)
    return app
