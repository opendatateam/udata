# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from importlib import import_module
from os.path import join, dirname, isdir, exists

from flask import current_app
from webassets.filter import get_filter

from flask.ext.assets import YAMLLoader, Bundle
from flask.ext.themes2 import Themes, Theme, render_theme_template, get_theme, packaged_themes_loader

from . import assets


log = logging.getLogger(__name__)


themes = Themes()


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


def plugin_theme_loader(app):
    for plugin in app.config['PLUGINS']:
        module = import_module('udata.ext.{0}'.format(plugin))
        path = join(dirname(module.__file__), 'theme')
        if isdir(path):
            yield Theme(path)


def render(template, **context):
    '''
    Render a template with uData frontend specifics

        * Theme
    '''
    theme = current_app.config['THEME']
    return render_theme_template(get_theme(theme), template, **context)


def init_app(app):
    themes.init_themes(app, app_identifier='udata', loaders=[packaged_themes_loader, plugin_theme_loader])

    # Hook into flask security to user themed auth pages
    app.config.setdefault('SECURITY_RENDER', 'udata.frontend:render')

    # Load all theme assets
    theme = app.theme_manager.themes[app.config['THEME']]
    app.config['STATIC_DIRS'].append(('', theme.static_path))
    if isdir(join(theme.static_path, 'less')):
        app.config['LESS_PATHS'].append(join(theme.static_path, 'less'))
    if exists(join(theme.path, 'assets.yaml')):
        bundles = ThemeYAMLLoader(theme).load_bundles()
        for name in bundles:
            assets.register(name, bundles[name])
