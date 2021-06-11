import inspect
import logging

from importlib import import_module
from jinja2 import Markup

from udata import assets, entrypoints

from .markdown import UdataCleaner, init_app as init_markdown


log = logging.getLogger(__name__)


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
