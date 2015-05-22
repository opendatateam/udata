# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from importlib import import_module
# from os.path import join
# from pkg_resources import resource_stream

from flask import abort

# from udata.app import ROOT_DIR
from udata.i18n import I18nBlueprint

from .markdown import md, init_app as init_markdown


log = logging.getLogger(__name__)

front = I18nBlueprint('front', __name__)


# Important: import after assets declaration
from .. import theme


_footer_snippets = []


def footer_snippet(func):
    _footer_snippets.append(func)
    return func


@front.app_context_processor
def inject_footer_snippets():
    return {'footer_snippets': _footer_snippets}


@front.app_context_processor
def inject_current_theme():
    return {'current_theme': theme.current}


def _load_views(app, module):
    try:
        views = import_module(module)
        blueprint = getattr(views, 'blueprint', None)
        if blueprint:
            app.register_blueprint(blueprint)
    except ImportError as e:
        pass
    except Exception as e:
        log.error('Error importing %s views: %s', module, e)


def init_app(app):
    init_markdown(app)

    from . import helpers, error_handlers

    # Load all core views and blueprint
    import udata.core.search.views

    from udata.core.storages.views import blueprint as storages_blueprint
    from udata.core.user.views import blueprint as user_blueprint
    from udata.core.site.views import noI18n, blueprint as site_blueprint
    from udata.core.dataset.views import blueprint as dataset_blueprint
    from udata.core.reuse.views import blueprint as reuse_blueprint
    from udata.core.organization.views import blueprint as org_blueprint
    from udata.core.followers.views import blueprint as follow_blueprint
    from udata.core.topic.views import blueprint as topic_blueprint
    from udata.core.post.views import blueprint as post_blueprint
    from udata.core.tags.views import bp as tags_blueprint
    from udata.core.faq.views import bp as faq_blueprint

    app.register_blueprint(storages_blueprint)
    app.register_blueprint(user_blueprint)
    app.register_blueprint(noI18n)
    app.register_blueprint(site_blueprint)
    app.register_blueprint(dataset_blueprint)
    app.register_blueprint(reuse_blueprint)
    app.register_blueprint(org_blueprint)
    app.register_blueprint(follow_blueprint)
    app.register_blueprint(topic_blueprint)
    app.register_blueprint(post_blueprint)
    app.register_blueprint(tags_blueprint)
    app.register_blueprint(faq_blueprint)

    # Load all plugins views and blueprints
    for plugin in app.config['PLUGINS']:
        module = 'udata.ext.{0}.views'.format(plugin)
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

    # Load debug toolbar if enabled
    if app.config.get('DEBUG_TOOLBAR'):
        from flask.ext.debugtoolbar import DebugToolbarExtension
        DebugToolbarExtension(app)
