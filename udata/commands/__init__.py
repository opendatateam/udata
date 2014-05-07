# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from os.path import join, dirname, splitext, basename
from glob import iglob

from flask.ext.script import Manager
from flask.ext.script.commands import Clean, ShowUrls, Server


from udata.app import create_app, standalone
from udata.core import MODULES

log = logging.getLogger(__name__)

manager = Manager()


def register_commands(manager):
    '''Register all core commands'''
    manager.add_command('clean', Clean())
    manager.add_command('urls', ShowUrls())
    manager.add_command('serve', Server(port=6666, use_debugger=True, use_reloader=True))

    # Load all commands submodule
    for filename in iglob(join(dirname(__file__), '[!_]*.py')):
        module = splitext(basename(filename))[0]
        try:
            __import__('udata.commands.{0}'.format(module))
        except Exception as e:
            log.error('Unable to import %s: %s', module, e)

    # Load all coremodules commands
    for module in MODULES:
        try:
            __import__('udata.core.{0}.commands'.format(module))
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s commands: %s', module, e)

    # Dynamic module commands loading
    for plugin in manager.app.config['PLUGINS']:
        name = 'udata.ext.{0}.commands'.format(plugin)
        try:
            __import__(name)
        except ImportError:
            pass
        except Exception as e:
            log.error('Error importing %s: %s', name, e)


def run_manager(config='udata.settings.Defaults'):
    app = create_app(config)
    app = standalone(app)
    manager.app = app
    register_commands(manager)
    manager.run()


def console_script():
    run_manager()
