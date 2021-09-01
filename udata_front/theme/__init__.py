import pkgutil
import pkg_resources
import os
import logging
from time import time
from werkzeug.local import LocalProxy
from flask import g, current_app

from flask_themes2 import (
    Themes, Theme, render_theme_template, get_theme
)
from jinja2 import contextfunction
from udata import assets


log = logging.getLogger(__name__)


themes = Themes()


def get_current_theme():
    if getattr(g, 'theme', None) is None:
        g.theme = current_app.theme_manager.themes[current_app.config['THEME']]
        g.theme.configure()
    return g.theme


current = LocalProxy(get_current_theme)


@contextfunction
def theme_static_with_version(ctx, filename, external=False):
    '''Override the default theme static to add cache burst'''
    if current_app.theme_manager.static_folder:
        url = assets.cdn_for('_themes.static',
                             filename=current.identifier + '/' + filename,
                             _external=external)
    else:
        url = assets.cdn_for('_themes.static',
                             themeid=current.identifier,
                             filename=filename,
                             _external=external)
    if url.endswith('/'):  # this is a directory, no need for cache burst
        return url
    if current_app.config['DEBUG']:
        burst = time()
    else:
        burst = current.entrypoint.dist.version
    return '{url}?_={burst}'.format(url=url, burst=burst)


class ConfigurableTheme(Theme):
    context_processors = None
    defaults = None
    admin_form = None
    manifest = None
    _menu = None
    _configured = False

    def __init__(self, entrypoint):
        self.entrypoint = entrypoint
        # Compute path without loading the module
        path = pkgutil.get_loader(entrypoint.module_name).path
        path = os.path.dirname(path)
        super(ConfigurableTheme, self).__init__(path)

        self.variants = self.info.get('variants', [])
        if 'gouvfr' not in self.variants:
            self.variants.insert(0, 'gouvfr')
        self.context_processors = {}

        # Check JSON manifest
        manifest = os.path.join(path, 'manifest.json')
        if os.path.exists(manifest):
            self.manifest = manifest

    @property
    def site(self):
        from udata.core.site.models import current_site
        return current_site

    @property
    def config(self):
        return self.site.themes.get(self.identifier)

    @property
    def menu(self):
        return self._menu

    @menu.setter
    def menu(self, value):
        self._menu = value

    @property
    def variant(self):
        '''Get the current theme variant'''
        variant = current_app.config['THEME_VARIANT']
        if variant not in self.variants:
            log.warning('Unkown theme variant: %s', variant)
            return 'gouvfr'
        else:
            return variant

    def configure(self):
        if self._configured:
            return
        self.entrypoint.load()
        if self.defaults and self.identifier not in self.site.themes:
            self.site.themes[self.identifier] = self.defaults
            try:
                self.site.save()
            except Exception:
                log.exception('Unable to save theme configuration')
        self._configured = True

    def get_processor(self, context_name, default=lambda c: c):
        return self.context_processors.get(context_name, default)


def themes_loader(app):
    '''Load themes from entrypoints'''
    for entrypoint in pkg_resources.iter_entry_points('udata.themes'):
        yield ConfigurableTheme(entrypoint)


def render(template, **context):
    '''
    Render a template with uData frontend specifics

        * Theme
    '''
    theme = current_app.config['THEME']
    return render_theme_template(get_theme(theme), template, **context)


def defaults(values):
    g.theme.defaults = values


def menu(navbar):
    g.theme.menu = navbar


def context(name):
    '''A decorator for theme context processors'''
    def wrapper(func):
        g.theme.context_processors[name] = func
        return func
    return wrapper


def init_app(app):
    app.config.setdefault('THEME_VARIANT', 'gouvfr')

    themes.init_themes(app, app_identifier='udata', loaders=[themes_loader])
    # Load all theme assets
    try:
        theme = app.theme_manager.themes[app.config['THEME']]
    except KeyError:
        theme = app.theme_manager.themes['gouvfr']
    prefix = '/'.join(('_themes', theme.identifier))
    app.config['STATIC_DIRS'].append((prefix, theme.static_path))

    # Override the default theme_static
    app.jinja_env.globals['theme_static'] = theme_static_with_version

    # Load manifest if necessary
    if theme.manifest:
        with app.app_context():
            assets.register_manifest('theme', theme.manifest)

    # Hook into flask security to user themed auth pages
    app.config.setdefault('SECURITY_RENDER', 'udata_front.theme:render')

    @app.context_processor
    def inject_current_theme():
        return {'current_theme': current}
