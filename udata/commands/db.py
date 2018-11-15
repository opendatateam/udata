import logging

import click

from os.path import join
from pkg_resources import resource_isdir, resource_listdir, resource_string

from flask import current_app

from pymongo.errors import PyMongoError, OperationFailure
from mongoengine.connection import get_db

from udata.commands import cli, green, yellow, cyan, red, magenta, echo
from udata.migrations import manager

log = logging.getLogger(__name__)


@cli.group('db')
def grp():
    '''Database related operations'''
    pass


# A migration script wrapper recording the stdout lines
SCRIPT_WRAPPER = '''
function(plugin, filename, script) {{
    var stdout = [];
    function print() {{
        var args = Array.prototype.slice.call(arguments);
        stdout.push(args.join(' '));
    }}

    {0}

    db.migrations.insert({{
        plugin: plugin,
        filename: filename,
        date: ISODate(),
        script: script,
        output: stdout.join('\\n')
    }});

    return stdout;
}}
'''

# Date format used to for display
DATE_FORMAT = '%Y-%m-%d %H:%M'


def normalize_migration(plugin_or_specs, filename):
    if filename is None and ':' in plugin_or_specs:
        plugin, filename = plugin_or_specs.split(':')
    else:
        plugin = plugin_or_specs
    if not filename.endswith('.py'):
        filename += '.py'
    return plugin, filename


def log_status(plugin, filename, status):
    '''Properly display a migration status line'''
    display = ':'.join((plugin, filename)) + ' '
    log.info('%s [%s]', '{:.<70}'.format(display), status)


@grp.command()
def status():
    '''Display the database migrations status'''
    for plugin, package, filename in manager.available_migrations():
        migration = manager.get_migration(plugin, filename)
        if migration:
            status = green(migration['date'].strftime(DATE_FORMAT))
        else:
            status = yellow('Not applied')
        log_status(plugin, filename, status)


@grp.command()
@click.option('-r', '--record', is_flag=True,
              help='Only records the migrations')
@click.option('-d', '--dry-run', is_flag=True,
              help='Only print migrations to be applied')
def migrate(record, dry_run=False):
    '''Perform database migrations'''
    handler = manager.record_migration if record else manager.execute_migration
    success = True
    for plugin, package, filename in manager.available_migrations():
        migration = manager.get_migration(plugin, filename)
        if migration or not success:
            log_status(plugin, filename, cyan('Skipped'))
        else:
            status = magenta('Recorded') if record else yellow('Apply')
            log_status(plugin, filename, status)
            script = resource_string(package, join('migrations', filename))
            success &= handler(plugin, filename, dryrun=dry_run)


@grp.command()
@click.argument('plugin_or_specs')
@click.argument('filename', default=None, required=False, metavar='[FILENAME]')
def unrecord(plugin_or_specs, filename):
    '''
    Remove a database migration record.

    \b
    A record can be expressed with the following syntaxes:
     - plugin filename
     - plugin filename.js
     - plugin:filename
     - plugin:fliename.js
    '''
    plugin, filename = normalize_migration(plugin_or_specs, filename)
    removed = manager.unrecord_migration(plugin, filename)
    if removed:
        log.info('Removed migration %s:%s', plugin, filename)
    else:
        log.error('Migration not found %s:%s', plugin, filename)
