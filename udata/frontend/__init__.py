import inspect
import logging
import json
import pkg_resources

from time import time
from importlib import import_module
from jinja2 import Markup, contextfunction
from flask import current_app

from udata import assets, entrypoints
from udata.i18n import I18nBlueprint

from .markdown import UdataCleaner, init_app as init_markdown


log = logging.getLogger(__name__)


hook = I18nBlueprint('hook', __name__)

_template_hooks = {}


@hook.app_template_global()
def package_version(name):
    return pkg_resources.get_distribution(name).version


@hook.app_template_global(name='static')
def static_global(filename, _burst=True, **kwargs):
    if current_app.config['DEBUG'] or current_app.config['TESTING']:
        burst = time()
    else:
        burst = package_version('udata')
    if _burst:
        kwargs['_'] = burst
    return assets.cdn_for('static', filename=filename, **kwargs)


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


@contextfunction
def render_template_hook(ctx, name, *args, **kwargs):
    if not has_template_hook(name):
        return ''
    return HookRenderer(_template_hooks[name], ctx, *args, **kwargs)


@hook.app_context_processor
def inject_hooks():
    return {
        'hook': render_template_hook,
        'has_hook': has_template_hook,
    }


class SafeMarkup(Markup):
    '''Markup object bypasses Jinja's escaping. This override allows to sanitize the resulting html.'''
    def __new__(cls, base, *args, **kwargs):
        cleaner = UdataCleaner()
        return super().__new__(cls, cleaner.clean(base), *args, **kwargs)


def _load_views(app, module):
    views = module if inspect.ismodule(module) else import_module(module)
    blueprint = getattr(views, 'blueprint', None)
    if blueprint:
        app.register_blueprint(blueprint)


VIEWS = ['core.storages', 'core.tags', 'admin']


def init_app(app, views=None):
    views = views or VIEWS

    init_markdown(app)

    for view in views:
        _load_views(app, 'udata.{}.views'.format(view))

    # Load hook blueprint
    app.register_blueprint(hook)

    # Load all plugins views and blueprints
    for module in entrypoints.get_enabled('udata.views', app).values():
        _load_views(app, module)

    # Load all plugins views and blueprints
    for module in entrypoints.get_enabled('udata.front', app).values():
        front_module = module if inspect.ismodule(module) else import_module(module)
        front_module.init_app(app)
