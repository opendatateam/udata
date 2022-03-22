import inspect
from importlib import import_module
from flask import abort, current_app
from flask_navigation import Navigation
from udata import entrypoints
# included for retro-compatibility reasons (some plugins may import from here instead of udata)
from udata.frontend import template_hook  # noqa
from udata.i18n import I18nBlueprint

nav = Navigation()

front = I18nBlueprint('front', __name__)


@front.app_context_processor
def inject_current_theme():
    from udata_front import theme
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


VIEWS = ['gouvfr', 'dataset', 'organization', 'follower', 'post',
         'reuse', 'site', 'territories', 'topic', 'user']


def init_app(app):
    from udata_front import theme

    nav.init_app(app)
    theme.init_app(app)

    from . import helpers, error_handlers, resource_helpers  # noqa

    for view in VIEWS:
        _load_views(app, 'udata_front.views.{}'.format(view))

    # Load all plugins views and blueprints
    for module in entrypoints.get_enabled('udata.views', app).values():
        _load_views(app, module)

    # Optionally register debug views
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
