import inspect
import html
import logging
import json

from importlib import import_module
from jinja2 import Markup, contextfunction

from udata import assets, entrypoints
from udata.i18n import I18nBlueprint

from .markdown import UdataCleaner, init_app as init_markdown


log = logging.getLogger(__name__)


hook = I18nBlueprint('hook', __name__)

_template_hooks = {}


@hook.app_template_global()
def manifest(app, filename, **kwargs):
    return assets.from_manifest(app, filename, **kwargs)


@hook.app_template_global()
def in_manifest(filename, app='udata'):
    '''A Jinja test to check an asset existance in manifests'''
    return assets.exists_in_manifest(app, filename)


@hook.app_template_filter()
@hook.app_template_global()
def to_json(data):
    '''Convert data to JSON, you may have to use |safe after it.'''
    if not data:
        return Markup('')
    return json.dumps(data)


def json_ld_script_preprocessor(o):
    if isinstance(o, dict):
        return {k: json_ld_script_preprocessor(v) for k, v in o.items()}
    elif isinstance(o, (list, tuple)):
        return [json_ld_script_preprocessor(v) for v in o]
    elif isinstance(o, str):
        return html.escape(o).replace('&#x27;', '&apos;')
    else:
        return o


@hook.app_template_filter()
def embedded_json_ld(jsonld):
    '''
    Sanitize JSON-LD for <script> tag inclusion.

    JSON-LD accepts any string but there is a special case
    for script tag inclusion.
    See: https://w3c.github.io/json-ld-syntax/#restrictions-for-contents-of-json-ld-script-elements
    '''
    return Markup(json.dumps(json_ld_script_preprocessor(jsonld), ensure_ascii=False))


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

    # This piece of code checks wether or not a
    # front end is present in the plugins list.
    # If not, it adds a home views on the `/` route
    # to prevent 404 error when requesting the site's
    # home page and redirects to the admin home page.
    if 'front' not in app.config.get('PLUGINS'):
        views.append('core.site')

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

    # Load core manifest
    with app.app_context():
        assets.register_manifest('udata')
        for dist in entrypoints.get_plugins_dists(app, 'udata.views'):
            if assets.has_manifest(dist.project_name):
                assets.register_manifest(dist.project_name)
