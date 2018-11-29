import logging

import click

from udata.commands import cli, green, yellow, cyan, red, magenta, echo
from udata import migrations

# Date format used to for display
DATE_FORMAT = '%Y-%m-%d %H:%M'

log = logging.getLogger(__name__)


@cli.group('db')
def grp():
    '''Database related operations'''
    pass


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


def format_output(output, success=True):
    echo('│')
    for level, msg in output:
        echo('│ {0}'.format(msg))
    echo('│')
    echo('└──[{0}]'.format(green('OK') if success else red('KO')))
    echo('')


@grp.command()
def status():
    '''Display the database migrations status'''
    for plugin, package, filename in migrations.list_availables():
        record = migrations.get_record(plugin, filename)
        if record.ok:
            status = green(record.last_date.strftime(DATE_FORMAT))
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
    success = True
    for plugin, package, filename in migrations.list_availables():
        dbrecord = migrations.get_record(plugin, filename)
        if dbrecord.ok or not success:
            log_status(plugin, filename, cyan('Skipped'))
        else:
            status = magenta('Recorded') if record else yellow('Apply')
            log_status(plugin, filename, status)
            try:
                output = migrations.execute(plugin, filename, package,
                                            recordonly=record,
                                            dryrun=dry_run)
            except migrations.MigrationError as me:
                output = me.output
                success = False
            format_output(output, success)
    return success


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
    removed = migrations.unrecord(plugin, filename)
    if removed:
        log.info('Removed migration %s:%s', plugin, filename)
    else:
        log.error('Migration not found %s:%s', plugin, filename)
