# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import imp
import logging

from importlib import import_module
from os.path import join, dirname, isdir, exists

from flask import current_app, g
from webassets.filter import get_filter
from werkzeug.local import LocalProxy

from flask.ext.assets import YAMLLoader, Bundle
from flask.ext.themes2 import Themes, Theme, render_theme_template, get_theme, packaged_themes_loader

from udata.i18n import lazy_gettext as _

from . import assets, nav


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
        self.context_processors = {}

    @property
    def site(self):
        from udata.core.site.views import current_site
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

    def configure(self):
        if self._configured:
            return
        config_path = join(self.path, 'theme.py')
        if exists(config_path):
            imp.load_source('udata.frontend.theme.{0}'.format(self.identifier), config_path)
        if self.defaults and self.identifier not in self.site.themes:
            self.site.themes[self.identifier] = self.defaults
            try:
                self.site.save()
            except:
                log.exception('Unable to save theme configuration')
        self._configured = True

    def get_processor(self, context_name, default=lambda c: c):
        return self.context_processors.get(context_name, default)


class ThemeYAMLLoader(YAMLLoader):
    '''
    YAML theme assets loaders

    Loads assets from theme assets.yaml file if present
    and handle path rewriting
    '''
    def __init__(self, theme):
        super(ThemeYAMLLoader, self).__init__(join(theme.path, 'assets.yaml'))
        self.theme = theme

    def _yield_bundle_contents(self, data):
        for content in super(ThemeYAMLLoader, self)._yield_bundle_contents(data):
            if isinstance(content, basestring):
                theme_content = join(self.theme.static_path, content)
                if exists(theme_content):
                    yield theme_content
                    continue
            yield content

    def _dependencies_from_theme(self, dependencies):
        if not dependencies:
            return None

        deps = []
        for dependency in dependencies:
            deps.append(dependency)
            deps.append(join(self.theme.static_path, dependency))
        return deps

    def _get_bundle(self, data):
        """Return a bundle initialised by the given dict."""
        filters = data.get('filters', None)
        if filters and 'cssrewrite' in filters:
            filters = [self.cssrewrite() if f == 'cssrewrite' else f for f in filters.split(',')]

        kwargs = dict(
            filters=filters,
            output=data.get('output', None),
            debug=data.get('debug', None),
            extra=data.get('extra', {}),
            depends=self._dependencies_from_theme(data.get('depends', None))
        )
        return Bundle(*list(self._yield_bundle_contents(data)), **kwargs)

    def cssrewrite(self):
        return get_filter('cssrewrite', replace={
            # self.theme.path: '',
            self.theme.static_path: '_themes/{0}'.format(self.theme.name),
        })


def udata_themes_loader(app):
    for theme in packaged_themes_loader(app):
        yield ConfigurableTheme(theme.path)


def plugin_themes_loader(app):
    for plugin in app.config['PLUGINS']:
        module = import_module('udata.ext.{0}'.format(plugin))
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


def admin_form(cls):
    g.theme.admin_form = cls
    return cls


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
    themes.init_themes(app, app_identifier='udata', loaders=[udata_themes_loader, plugin_themes_loader])

    # Load all theme assets
    theme = app.theme_manager.themes[app.config['THEME']]
    app.config['STATIC_DIRS'].append(('', theme.static_path))

    if isdir(join(theme.static_path, 'less')):
        app.config['LESS_PATHS'].append(join(theme.static_path, 'less'))

    if exists(join(theme.path, 'assets.yaml')):
        bundles = ThemeYAMLLoader(theme).load_bundles()
        for name in bundles:
            assets.register(name, bundles[name])
