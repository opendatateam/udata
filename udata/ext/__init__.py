# -*- coding: utf-8 -*-
"""
    udata.ext
    ~~~~~~~~~

    Redirect imports for extensions.  This module basically makes it possible
    for us to transition from flaskext.foo to flask_foo without having to
    force all extensions to upgrade at the same time.

    When a user does ``from flask_foo import bar`` it will attempt to
    import ``from flask_foo import bar`` first and when that fails it will
    try to import ``from flaskext.foo import bar``.

    We're switching from namespace packages because it was just too painful for
    everybody involved.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from importlib import import_module


def setup():
    # TODO: change this mecanism to drop the deprecated ExtensionImporter
    from flask.exthook import ExtensionImporter
    importer = ExtensionImporter(['udata_%s', 'udataext.%s'], __name__)
    importer.install()


setup()
del setup


def init_app(app):
    '''Initialize all extensions'''
    for plugin in app.config['PLUGINS']:
        name = 'udata.ext.{0}'.format(plugin)
        plugin = import_module(name)
        if hasattr(plugin, 'init_app') and callable(plugin.init_app):
            plugin.init_app(app)
