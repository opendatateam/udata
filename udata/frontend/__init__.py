import inspect
import logging
from importlib import import_module
from time import time

import pkg_resources
from flask import current_app
from jinja2 import pass_context
from markupsafe import Markup

from udata import assets, entrypoints
from udata.i18n import I18nBlueprint

from .markdown import UdataCleaner
from .markdown import init_app as init_markdown

log = logging.getLogger(__name__)


hook = I18nBlueprint("hook", __name__)

_template_hooks = {}


@hook.app_template_global()
def package_version(name: str) -> str:
    return pkg_resources.get_distribution(name).version


@hook.app_template_global(name="static")
def static_global(filename, _burst=True, **kwargs):
    if current_app.config["DEBUG"] or current_app.config["TESTING"]:
        burst = time()
    else:
        burst = package_version("udata")
    if _burst:
        kwargs["_"] = burst
    return assets.cdn_for("static", filename=filename, **kwargs)


@hook.app_template_filter()
def avatar_placeholder(url):
    if url:
        return url

    return "data:image/png;base64,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"


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
        return Markup(
            "".join(
                f(self.ctx, *self.args, **self.kwargs)
                for f, w in self.funcs
                if w is None or w(self.ctx)
            )
        )

    def __iter__(self):
        for func, when in self.funcs:
            if when is None or when(self.ctx):
                yield Markup(func(self.ctx, *self.args, **self.kwargs))


@pass_context
def render_template_hook(ctx, name, *args, **kwargs):
    if not has_template_hook(name):
        return ""
    return HookRenderer(_template_hooks[name], ctx, *args, **kwargs)


@hook.app_context_processor
def inject_hooks():
    return {
        "hook": render_template_hook,
        "has_hook": has_template_hook,
    }


class SafeMarkup(Markup):
    """Markup object bypasses Jinja's escaping. This override allows to sanitize the resulting html."""

    def __new__(cls, base, *args, **kwargs):
        cleaner = UdataCleaner()
        return super().__new__(cls, cleaner.clean(base), *args, **kwargs)


def _load_views(app, module):
    views = module if inspect.ismodule(module) else import_module(module)
    blueprint = getattr(views, "blueprint", None)
    if blueprint:
        app.register_blueprint(blueprint)


VIEWS = ["core.storages", "core.tags", "admin"]


def init_app(app, views=None):
    views = views or VIEWS

    init_markdown(app)

    for view in views:
        _load_views(app, "udata.{}.views".format(view))

    # Load hook blueprint
    app.register_blueprint(hook)

    # Load all plugins views and blueprints
    for module in entrypoints.get_enabled("udata.views", app).values():
        _load_views(app, module)

    # Load all plugins views and blueprints
    for module in entrypoints.get_enabled("udata.front", app).values():
        front_module = module if inspect.ismodule(module) else import_module(module)
        front_module.init_app(app)
