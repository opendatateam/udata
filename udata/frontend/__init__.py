import inspect
import logging

import bleach
from importlib import import_module

from flask import abort, current_app
from jinja2 import Markup, contextfunction

from udata import assets, entrypoints
from udata.i18n import I18nBlueprint

from .markdown import UdataCleaner, init_app as init_markdown

from .. import theme


log = logging.getLogger(__name__)

front = I18nBlueprint('front', __name__)

_template_hooks = {}


def _wrapper(func, name=None, when=None):
    name = name or func.__name__
    if name not in _template_hooks:
        _template_hooks[name] = []
    _template_hooks[name].append((func, when))
    return func


def template_hook(func_or_name, when=None):
    if callable(func_or_name):
        return _wrapper(func_or_name)
    elif isinstance(func_or_name, str):
        def wrapper(func):
            return _wrapper(func, func_or_name, when=when)
        return wrapper


def has_template_hook(name):
    return name in _template_hooks


class HookRenderer:
    def __init__(self, funcs, ctx, *args, **kwargs):
        self.funcs = funcs
        self.ctx = ctx
        self.args = args
        self.kwargs = kwargs

    def __html__(self):
        return Markup(''.join(
            f(self.ctx, *self.args, **self.kwargs)
            for f, w in self.funcs
            if w is None or w(self.ctx)
        ))

    def __iter__(self):
        for func, when in self.funcs:
            if when is None or when(self.ctx):
                yield Markup(func(self.ctx, *self.args, **self.kwargs))


class SafeMarkup(Markup):
    '''Markup object bypasses Jinja's escaping. This override allows to sanitize the resulting html.'''
    def __new__(cls, base, *args, **kwargs):
        cleaner = UdataCleaner()
        return super().__new__(cls, cleaner.clean(base), *args, **kwargs)


@contextfunction
def render_template_hook(ctx, name, *args, **kwargs):
    if not has_template_hook(name):
        return ''
    return HookRenderer(_template_hooks[name], ctx, *args, **kwargs)


@front.app_context_processor
def inject_hooks():
    return {
        'hook': render_template_hook,
        'has_hook': has_template_hook,
    }


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

    # Load core manifest
    with app.app_context():
        assets.register_manifest('udata')
        for dist in entrypoints.get_plugins_dists(app, 'udata.views'):
            if assets.has_manifest(dist.project_name):
                assets.register_manifest(dist.project_name)

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
