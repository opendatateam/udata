# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import inspect
import logging

from importlib import import_module

from flask import abort, current_app

from udata import entrypoints
from udata.i18n import I18nBlueprint

from .markdown import init_app as init_markdown

from .. import theme


log = logging.getLogger(__name__)

front = I18nBlueprint('front', __name__)

_footer_snippets = []
_template_hooks = {}


def footer_snippet(func):
    _footer_snippets.append(func)
    return func


def template_hook(func):
    _template_hooks[func.__name__] = func
    return func


@front.app_context_processor
def inject_template_hooks():
    return {'hook_%s' % k: v for (k, v) in _template_hooks.items()}


@front.app_context_processor
def inject_footer_snippets():
    return {'footer_snippets': _footer_snippets}


@front.app_context_processor
def inject_current_theme():
    return {'current_theme': theme.current}


@front.app_context_processor
def inject_cache_duration():
    return {
        'cache_duration': 60 * current_app.config['TEMPLATE_CACHE_DURATION']
    }


def _load_views(app, module):
    views = module if inspect.ismodule(module) else import_module(module)
    blueprint = getattr(views, 'blueprint', None)
    if blueprint:
        app.register_blueprint(blueprint)


VIEWS = ['core.storages', 'core.user', 'core.site', 'core.dataset',
         'core.reuse', 'core.organization', 'core.followers',
         'core.topic', 'core.post', 'core.tags', 'admin', 'search',
         'features.territories']


def init_app(app, views=None):
    views = views or VIEWS

    init_markdown(app)

    from . import helpers, error_handlers  # noqa

    for view in views:
        _load_views(app, 'udata.{}.views'.format(view))

    # Load all plugins views and blueprints
    for module in entrypoints.get_enabled('udata.views', app).values():
        _load_views(app, module)

    # Optionnaly register debug views
    if app.config.get('DEBUG'):
        @front.route('/403/')
        def test_403():
            abort(403)

        @front.route('/404/')
        def test_404():
            abort(404)

        @front.route('/500/')
        def test_500():
            abort(500)

    # Load front only views and helpers
    app.register_blueprint(front)

    # Enable CDN if required
    if app.config['CDN_DOMAIN'] is not None:
        from flask_cdn import CDN
        CDN(app)

    # Load debug toolbar if enabled
    if app.config.get('DEBUG_TOOLBAR'):
        from flask_debugtoolbar import DebugToolbarExtension
        DebugToolbarExtension(app)
