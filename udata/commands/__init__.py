# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os
import click
import sys
import logging
import pkg_resources

from glob import iglob

from flask.cli import FlaskGroup, shell_command
from udata.app import create_app, standalone, VERBOSE_LOGGERS

# Expect an utf8 compatible terminal
reload(sys)  # noqa
sys.setdefaultencoding('utf8')

log = logging.getLogger(__name__)

IS_TTY = sys.__stdin__.isatty()

INFO = '➢'
DEBUG = '⇝'
OK = '✔'
KO = '✘'
WARNING = '⚠'

CONTEXT_SETTINGS = {
    'auto_envvar_prefix': 'udata',
    'help_option_names': ['-?', '-h', '--help'],
}

click.disable_unicode_literals_warning = True


def color(name, **kwargs):
    return lambda t: click.style(str(t), fg=name, **kwargs)


green = color('green', bold=True)
yellow = color('yellow', bold=True)
red = color('red', bold=True)
cyan = color('cyan')
magenta = color('magenta', bold=True)
white = color('white', bold=True)
echo = click.echo


def header(msg):
    '''Display an header'''
    echo(' '.join((yellow('✯'), green(msg))))


def success(msg):
    echo('{0} {1}'.format(green(OK), white(msg)))


def error(msg, details=None):
    msg = '{0} {1}'.format(red(KO), white(msg))
    if details:
        msg = '\n'.join((msg, str(details)))
    echo(format_multiline(msg))


def exit(msg, details=None, code=-1):
    error(msg, details)
    sys.exit(code)


LEVEL_COLORS = {
    logging.DEBUG: cyan,
    logging.WARNING: yellow,
    logging.ERROR: red,
    logging.CRITICAL: color('black', bg='red', bold=True),
}

LEVELS_PREFIX = {
    logging.INFO: cyan(INFO),
    logging.WARNING: yellow(WARNING),
}


def format_multiline(string):
    string = string.replace('\n', '\n│ ')
    return replace_last(string, '│', '└')


def replace_last(string, char, replacement):
    return replacement.join(string.rsplit(char, 1))


class CliFormatter(logging.Formatter):
    """
    Convert a `logging.LogRecord' object into colored text, using ANSI
    escape sequences.
    """
    def format(self, record):
        if not IS_TTY:
            return super(CliFormatter, self).format(record)
        record.msg = format_multiline(str(record.msg))
        record.msg = ' '.join((self._prefix(record), record.msg))
        return super(CliFormatter, self).format(record)

    def formatException(self, ei):
        '''Indent traceback info for better readability'''
        out = super(CliFormatter, self).formatException(ei)
        return '│' + format_multiline(out)

    def _prefix(self, record):
        if record.levelno in LEVELS_PREFIX:
            return LEVELS_PREFIX[record.levelno]
        else:
            color = LEVEL_COLORS.get(record.levelno, white)
            return '{0}:'.format(color(record.levelname.upper()))


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

    app.logger.setLevel(log_level)
    app.logger.handlers = []
    app.logger.addHandler(handler)

    logger = logging.getLogger('__main__')
    logger.setLevel(log_level)
    logger.handlers = []
    logger.addHandler(handler)

    for name in app.config['PLUGINS']:
        logger = logging.getLogger('udata_{0}'.format(name))
        logger.setLevel(log_level)
        logger.handlers = []
        logger.addHandler(handler)

    for name in VERBOSE_LOGGERS:
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
        logger.handlers = []
        logger.addHandler(handler)

    return app


def create_cli_app(info):
    app = create_app('udata.settings.Defaults', init_logging=init_logging)
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
    def _load_plugin_commands(self):
        if self._loaded_plugin_commands:
            return

        # Load all commands submodule
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

        # Load commands from entry points
        for ep in pkg_resources.iter_entry_points('udata.commands'):
            self.add_command(ep.load(), ep.name)
        super(UdataGroup, self)._load_plugin_commands()


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
