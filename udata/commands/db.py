# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import click

from os.path import join
from pkg_resources import resource_isdir, resource_listdir, resource_string

from flask import current_app

from pymongo.errors import PyMongoError, OperationFailure
from mongoengine.connection import get_db

from udata import entrypoints
from udata.commands import cli, green, yellow, cyan, red, magenta, echo

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

# Only record a migration script
RECORD_WRAPPER = '''
function(plugin, filename, script) {
    db.migrations.insert({
        plugin: plugin,
        filename: filename,
        date: ISODate(),
        script: script,
        output: 'Recorded only'
    });
}
'''

# Only record a migration script
UNRECORD_WRAPPER = '''
function(oid) {{
    db.migrations.remove({_id: oid});
}}
'''

# Date format used to for display
DATE_FORMAT = '%Y-%m-%d %H:%M'


def normalize_migration(plugin_or_specs, filename):
    if filename is None and ':' in plugin_or_specs:
        plugin, filename = plugin_or_specs.split(':')
    else:
        plugin = plugin_or_specs
    if not filename.endswith('.js'):
        filename += '.js'
    return plugin, filename


def get_migration(plugin, filename):
    '''Get an existing migration record if exists'''
    db = get_db()
    return db.migrations.find_one({'plugin': plugin, 'filename': filename})


def execute_migration(plugin, filename, script, dryrun=False):
    '''Execute and record a migration'''
    db = get_db()
    js = SCRIPT_WRAPPER.format(script)
    lines = script.splitlines()
    success = True
    if not dryrun:
        try:
            lines = db.eval(js, plugin, filename, script)
        except OperationFailure as e:
            log.error(e.details['errmsg'].replace('\n', '\\n'))
            success = False
        except PyMongoError as e:
            log.error('Unable to apply migration: %s', str(e))
            success = False
    echo('│'.encode('utf8'))
    for line in lines:
        echo('│ {0}'.format(line).encode('utf8'))
    echo('│'.encode('utf8'))
    echo('└──[{0}]'.format(green('OK') if success else red('KO')).encode('utf8'))
    echo('')
    return success


def record_migration(plugin, filename, script, **kwargs):
    '''Only record a migration without applying it'''
    db = get_db()
    db.eval(RECORD_WRAPPER, plugin, filename, script)
    return True


def available_migrations():
    '''
    List available migrations for udata and enabled plugins

    Each row is tuple with following signature:

        (plugin, package, filename)
    '''
    migrations = []
    for filename in resource_listdir('udata', 'migrations'):
        if filename.endswith('.js'):
            migrations.append(('udata', 'udata', filename))

    plugins = entrypoints.get_enabled('udata.models', current_app)
    for plugin, module in plugins.items():
        if resource_isdir(module.__name__, 'migrations'):
            for filename in resource_listdir(module.__name__, 'migrations'):
                if filename.endswith('.js'):
                    migrations.append((plugin, module.__name__, filename))
    return sorted(migrations, key=lambda r: r[2])


def log_status(plugin, filename, status):
    '''Properly display a migration status line'''
    display = ':'.join((plugin, filename)) + ' '
    log.info('%s [%s]', '{:.<70}'.format(display), status)


@grp.command()
def status():
    '''Display the database migrations status'''
    for plugin, package, filename in available_migrations():
        migration = get_migration(plugin, filename)
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
    handler = record_migration if record else execute_migration
    success = True
    for plugin, package, filename in available_migrations():
        migration = get_migration(plugin, filename)
        if migration or not success:
            log_status(plugin, filename, cyan('Skipped'))
        else:
            status = magenta('Recorded') if record else yellow('Apply')
            log_status(plugin, filename, status)
            script = resource_string(package, join('migrations', filename))
            success &= handler(plugin, filename, script, dryrun=dry_run)


@grp.command()
@click.argument('plugin_or_specs')
@click.argument('filename', default=None, required=False, metavar='[FILENAME]')
def unrecord(plugin_or_specs, filename):
    '''
    Remove a database migration record.

    \b
    A record can be expressed with the following syntaxes:
     - plugin filename
     - plugin fliename.js
     - plugin:filename
     - plugin:fliename.js
    '''
    plugin, filename = normalize_migration(plugin_or_specs, filename)
    migration = get_migration(plugin, filename)
    if migration:
        log.info('Removing migration %s:%s', plugin, filename)
        db = get_db()
        db.eval(UNRECORD_WRAPPER, migration['_id'])
    else:
        log.error('Migration not found %s:%s', plugin, filename)
