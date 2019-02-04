# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging
import os
import pkg_resources
import sys

from glob import iglob

import click

from flask.cli import FlaskGroup, shell_command, ScriptInfo
from udata import entrypoints
from udata.app import create_app, standalone, VERBOSE_LOGGERS
from udata.utils import safe_unicode

log = logging.getLogger(__name__)

IS_TTY = sys.__stdin__.isatty()

INFO = '➢'.encode('utf8')
DEBUG = '⇝'.encode('utf8')
OK = '✔'.encode('utf8')
KO = '✘'.encode('utf8')
WARNING = '⚠'.encode('utf8')
HEADER = '✯'.encode('utf8')

NO_CAST = (int, float, bool)

CONTEXT_SETTINGS = {
    'auto_envvar_prefix': 'udata',
    'help_option_names': ['-?', '-h', '--help'],
}

click.disable_unicode_literals_warning = True


def color(name, **kwargs):
    return lambda t: click.style(str(t), fg=name, **kwargs).decode('utf8')


green = color('green', bold=True)
yellow = color('yellow', bold=True)
red = color('red', bold=True)
cyan = color('cyan', bold=True)
magenta = color('magenta', bold=True)
white = color('white', bold=True)
echo = click.echo


def header(msg):
    '''Display an header'''
    echo(' '.join((yellow(HEADER), white(safe_unicode(msg)), yellow(HEADER))))


def success(msg):
    '''Display a success message'''
    echo('{0} {1}'.format(green(OK), white(safe_unicode(msg))))


def error(msg, details=None):
    '''Display an error message with optional details'''
    msg = '{0} {1}'.format(red(KO), white(safe_unicode(msg)))
    msg = safe_unicode(msg)
    if details:
        msg = b'\n'.join((msg, safe_unicode(details)))
    echo(format_multiline(msg))


def exit_with_error(msg, details=None, code=-1):
    '''Exit with error'''
    error(msg, details)
    sys.exit(code)


LEVEL_COLORS = {
    logging.DEBUG: cyan,
    logging.WARNING: yellow,
    logging.ERROR: red,
    logging.CRITICAL: color('white', bg='red', bold=True),
}

LEVELS_PREFIX = {
    logging.INFO: cyan(INFO),
    logging.WARNING: yellow(WARNING),
}


def format_multiline(string):
    string = safe_unicode(string)
    string = string.replace(b'\n', b'\n│ ')
    return safe_unicode(replace_last(string, '│', '└'))


def replace_last(string, char, replacement):
    char = safe_unicode(char)
    replacement = safe_unicode(replacement)
    string = safe_unicode(string)
    return replacement.join(string.rsplit(char, 1))


class CliFormatter(logging.Formatter):
    """
    Convert a `logging.LogRecord' object into colored text, using ANSI
    escape sequences.
    """
    def format(self, record):
        if not IS_TTY:
            return super(CliFormatter, self).format(record)
        record.msg = format_multiline(record.msg)
        record.msg = b' '.join((self._prefix(record), record.msg))
        record.args = tuple(a if isinstance(a, NO_CAST) else safe_unicode(a)
                            for a in record.args)
        return super(CliFormatter, self).format(record)

    def formatException(self, ei):
        '''Indent traceback info for better readability'''
        out = super(CliFormatter, self).formatException(ei)
        return b'│' + format_multiline(out)

    def _prefix(self, record):
        if record.levelno in LEVELS_PREFIX:
            return safe_unicode(LEVELS_PREFIX[record.levelno])
        else:
            color = LEVEL_COLORS.get(record.levelno, white)
            return safe_unicode('{0}:'.format(color(record.levelname.upper())))


class CliHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            err = record.levelno >= logging.WARNING
            click.echo(msg, err=err)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)


def init_logging(app):
    log_level = logging.DEBUG if app.debug else logging.INFO

    handler = CliHandler()
    handler.setFormatter(CliFormatter())
    handler.setLevel(log_level)

    logger = logging.getLogger()
    logger.addHandler(handler)

    logger = logging.getLogger('__main__')
    logger.setLevel(log_level)
    logger.handlers = []
    logger.addHandler(handler)

    for name in entrypoints.get_roots():  # Entrypoints loggers
        logger = logging.getLogger(name)
        logger.setLevel(log_level)
        logger.handlers = []

    app.logger.setLevel(log_level)
    app.logger.handlers = []
    app.logger.addHandler(handler)

    for name in VERBOSE_LOGGERS:
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING if app.debug else logging.ERROR)
        logger.handlers = []

    return app


def create_cli_app(info):
    app = create_app(info.settings, init_logging=init_logging)
    return standalone(app)


MODULES_WITH_COMMANDS = [
    'api',
    'core.badges',
    'core.dataset',
    'core.jobs',
    'core.metrics',
    'core.organization',
    'core.spatial',
    'core.user',
    'harvest',
    'linkchecker',
    'search',
]


class UdataGroup(FlaskGroup):
    def __init__(self, *args, **kwargs):
        self._udata_commands_loaded = False
        super(UdataGroup, self).__init__(*args, **kwargs)

    def get_command(self, ctx, name):
        self.load_udata_commands(ctx)
        return super(UdataGroup, self).get_command(ctx, name)

    def list_commands(self, ctx):
        self.load_udata_commands(ctx)
        return super(UdataGroup, self).list_commands(ctx)

    def load_udata_commands(self, ctx):
        '''
        Load udata commands from:
        - `udata.commands.*` module
        - known internal modules with commands
        - plugins exporting a `udata.commands` entrypoint
        '''
        if self._udata_commands_loaded:
            return

        # Load all commands submodules
        pattern = os.path.join(os.path.dirname(__file__), '[!_]*.py')
        for filename in iglob(pattern):
            module = os.path.splitext(os.path.basename(filename))[0]
            try:
                __import__('udata.commands.{0}'.format(module))
            except Exception as e:
                error('Unable to import {0}'.format(module), e)

        # Load all core modules commands
        for module in MODULES_WITH_COMMANDS:
            try:
                __import__('udata.{0}.commands'.format(module))
            except Exception as e:
                error('Unable to import {0}'.format(module), e)

        # Load commands from entry points for enabled plugins
        app = ctx.ensure_object(ScriptInfo).load_app()
        entrypoints.get_enabled('udata.commands', app)

        # Ensure loading happens once
        self._udata_commands_loaded = False

    def main(self, *args, **kwargs):
        '''
        Instanciate ScriptInfo before parent does
        to ensure the `settings` parameters is available to `create_app
        '''
        obj = kwargs.get('obj')
        if obj is None:
            obj = ScriptInfo(create_app=self.create_app)
        # This is the import line: allows create_app to access the settings
        obj.settings = kwargs.pop('settings', 'udata.settings.Defaults')
        kwargs['obj'] = obj
        return super(UdataGroup, self).main(*args, **kwargs)


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(pkg_resources.get_distribution('udata').version)
    ctx.exit()


@click.group(context_settings=CONTEXT_SETTINGS,
             cls=UdataGroup, create_app=create_cli_app,
             add_version_option=False, add_default_commands=False)
@click.option('--version', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
def cli():
    '''udata management client'''


# Adds the default flask shell command
cli.add_command(shell_command)

if __name__ == '__main__':  # pragma: no cover
    cli()
