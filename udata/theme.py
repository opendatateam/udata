# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import imp
import logging

from importlib import import_module
from os.path import join, dirname, isdir, exists

from flask import current_app, g
from werkzeug.local import LocalProxy

from flask_themes2 import (
    Themes, Theme, render_theme_template, get_theme, packaged_themes_loader
)

from udata.app import nav
from udata.i18n import lazy_gettext as _

log = logging.getLogger(__name__)


themes = Themes()


def get_current_theme():
    if getattr(g, 'theme', None) is None:
        g.theme = current_app.theme_manager.themes[current_app.config['THEME']]
        g.theme.configure()
    return g.theme

current = LocalProxy(get_current_theme)


default_menu = nav.Bar('default_menu', [
    nav.Item(_('Organizations'), 'organizations.list'),
    nav.Item(_('Datasets'), 'datasets.list'),
    nav.Item(_('Reuses'), 'reuses.list'),
    nav.Item(_('Map'), 'site.map'),
])


class ConfigurableTheme(Theme):
    context_processors = None
    defaults = None
    admin_form = None
    _menu = None
    _configured = False

    def __init__(self, path):
        super(ConfigurableTheme, self).__init__(path)

        self.variants = self.info.get('variants', [])
        if 'default' not in self.variants:
            self.variants.insert(0, 'default')
        self.context_processors = {}

    @property
    def site(self):
        from udata.core.site.models import current_site
        return current_site

    @property
    def config(self):
        return self.site.themes.get(self.identifier)

    @property
    def menu(self):
        return self._menu or default_menu

    @menu.setter
    def menu(self, value):
        self._menu = value

    @property
    def variant(self):
        '''Get the current theme variant'''
        variant = current_app.config['THEME_VARIANT']
        if variant not in self.variants:
            log.warning('Unkown theme variant: %s', variant)
            return 'default'
        else:
            return variant

    def configure(self):
        if self._configured:
            return
        config_path = join(self.path, 'theme.py')
        if exists(config_path):
            imp.load_source('udata.frontend.theme.{0}'.format(self.identifier),
                            config_path)
        if self.defaults and self.identifier not in self.site.themes:
            self.site.themes[self.identifier] = self.defaults
            try:
                self.site.save()
            except:
                log.exception('Unable to save theme configuration')
        self._configured = True

    def get_processor(self, context_name, default=lambda c: c):
        return self.context_processors.get(context_name, default)


def udata_themes_loader(app):
    for theme in packaged_themes_loader(app):
        yield ConfigurableTheme(theme.path)


def plugin_themes_loader(app):
    for plugin in app.config['PLUGINS']:
        module = import_module('udata_{0}'.format(plugin))
        path = join(dirname(module.__file__), 'theme')
        if isdir(path):
            yield ConfigurableTheme(path)


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
    app.config.setdefault('THEME_VARIANT', 'default')
    themes.init_themes(app, app_identifier='udata',
                       loaders=[udata_themes_loader, plugin_themes_loader])

    # Load all theme assets
    theme = app.theme_manager.themes[app.config['THEME']]
    prefix = '/'.join(('_themes', theme.identifier))
    app.config['STATIC_DIRS'].append((prefix, theme.static_path))

    # Hook into flask security to user themed auth pages
    app.config.setdefault('SECURITY_RENDER', 'udata.theme:render')

    @app.context_processor
    def inject_current_theme():
        return {'current_theme': current}
