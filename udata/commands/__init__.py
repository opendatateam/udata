# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import sys

from os.path import join, dirname, splitext, basename
from glob import iglob

from flask.ext.script import Manager
from flask.ext.script.commands import Clean, ShowUrls, Server

from udata.app import create_app, standalone

# Expect an utf8 compatible terminal
reload(sys)
sys.setdefaultencoding('utf8')

log = logging.getLogger(__name__)

manager = Manager()


def submanager(name, **kwargs):
    sub_manager = Manager(**kwargs)
    manager.add_command(name, sub_manager)
    return sub_manager


def register_commands(manager):
    '''Register all core commands'''
    manager.add_command('clean', Clean())
    manager.add_command('urls', ShowUrls())

    settings = os.environ.get('UDATA_SETTINGS', join(os.getcwd(), 'udata.cfg'))
    manager.add_command('serve', Server(port=7000, use_debugger=True,
                                        use_reloader=True, threaded=True,
                                        extra_files=[settings]))

    # Load all commands submodule
    for filename in iglob(join(dirname(__file__), '[!_]*.py')):
        module = splitext(basename(filename))[0]
        try:
            __import__('udata.commands.{0}'.format(module))
        except Exception as e:
            log.error('Unable to import %s: %s', module, e)

    # Load all core modules commands
    import udata.core.metrics.commands
    import udata.core.user.commands
    import udata.core.dataset.commands
    import udata.core.organization.commands
    import udata.core.search.commands
    import udata.core.spatial.commands
    import udata.core.jobs.commands
    import udata.core.badges.commands
    import udata.api.commands
    import udata.harvest.commands

    # Dynamic module commands loading
    for plugin in manager.app.config['PLUGINS']:
        name = 'udata.ext.{0}.commands'.format(plugin)
        try:
            __import__(name)
        except ImportError as e:
            log.warning('Error importing %s: %s', name, e)
        except Exception as e:
            log.error('Error during import of %s: %s', name, e)


def run_manager(config='udata.settings.Defaults'):
    app = create_app(config)
    app = standalone(app)
    set_logging(app)
    manager.app = app
    register_commands(manager)
    manager.run()


def console_script():
    run_manager()


def set_logging(app):
    if (os.isatty(sys.stdout.fileno()) and not sys.platform.startswith('win')):
        fmt = ANSIFormatter()
    else:
        fmt = TextFormatter()

    log_level = logging.DEBUG if app.debug else logging.INFO

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(fmt)

    app.logger.setLevel(log_level)
    app.logger.handlers = []
    app.logger.addHandler(handler)

    for name in app.config['PLUGINS']:
        logger = logging.getLogger('udata_{0}'.format(name))
        logger.setLevel(log_level)
        logger.handlers = []
        logger.addHandler(handler)

    return app


class BaseFormatter(logging.Formatter):
    '''
    Common console formatting behavior
    '''
    def __init__(self, fmt=None, datefmt=None):
        FORMAT = '%(prefix)s %(message)s'
        super(BaseFormatter, self).__init__(fmt=FORMAT, datefmt=datefmt)

    def format(self, record):
        '''Customize the line prefix and indent multiline logs'''
        record.__dict__['prefix'] = self._prefix(record.levelname)
        record.msg = record.msg.replace('\n', '\n  | ')
        return super(BaseFormatter, self).format(record)

    def formatException(self, ei):
        '''Indent traceback info for better readability'''
        out = super(BaseFormatter, self).formatException(ei)
        out = str('\n').join(str('  | ') + line for line in out.splitlines())
        return out

    def _prefix(self, name):
        '''NOOP: overridden by subclasses'''
        return name


def color(code):
    '''A simple ANSI color wrapper factory'''
    return lambda t: '\033[{0}{1}\033[0;m'.format(code, t)


green = color('1;32m')
red = color('1;31m')
cyan = color('1;36m')
purple = color('1;35m')
yellow = color('1;33m')
white = color('1;37m')
bgred = color('1;41m')
bggrey = color('1;100m')


class ANSIFormatter(BaseFormatter):
    '''
    A log formatter that use ANSI colors.
    '''
    LEVEL_COLORS = {
        'INFO': cyan,
        'WARNING': yellow,
        'ERROR': red,
        'CRITICAL': bgred,
        'DEBUG': bggrey
    }

    def _prefix(self, name):
        level_color = self.LEVEL_COLORS.get(name, white)
        if name == 'INFO':
            return level_color('->')
        else:
            return '{0}:'.format(level_color(name))


class TextFormatter(BaseFormatter):
    '''
    A simple text-only formatter
    '''

    def _prefix(self, name):
        if name == 'INFO':
            return '->'
        else:
            return name + ':'
