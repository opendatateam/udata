import os
import logging

import click

from udata.commands import cli, green, yellow, cyan, red, magenta, white, echo
from udata import migrations

# Date format used to for display
DATE_FORMAT = '%Y-%m-%d %H:%M'

log = logging.getLogger(__name__)


@cli.group('db')
def grp():
    '''Database related operations'''
    pass


def log_status(migration, status):
    '''Properly display a migration status line'''
    name = os.path.splitext(migration.filename)[0]
    display = ':'.join((migration.plugin, name)) + ' '
    log.info('%s [%s]', '{:.<70}'.format(display), status)


def status_label(record):
    if record.ok:
        return green(record.last_date.strftime(DATE_FORMAT))
    elif not record.exists():
        return yellow('Not applied')
    else:
        return red(record.status)


def format_output(output, success=True, traceback=None):
    echo('  │')
    for level, msg in output:
        echo('  │ {0}'.format(msg))
    echo('  │')
    if traceback:
        for tb in traceback.split('\n'):
            echo('  │ {0}'.format(tb))
    echo('  │')
    echo('  └──[{0}]'.format(green('OK') if success else red('KO')))
    echo('')


@grp.command()
def status():
    '''Display the database migrations status'''
    for migration in migrations.list_available():
        log_status(migration, status_label(migration.record))


@grp.command()
@click.option('-r', '--record', is_flag=True,
              help='Only records the migrations')
@click.option('-d', '--dry-run', is_flag=True,
              help='Only print migrations to be applied')
def migrate(record, dry_run=False):
    '''Perform database migrations'''
    success = True
    for migration in migrations.list_available():
        if migration.record.ok or not success:
            log_status(migration, cyan('Skipped'))
        else:
            status = magenta('Recorded') if record else yellow('Apply')
            log_status(migration, status)
            try:
                output = migration.execute(recordonly=record, dryrun=dry_run)
            except migrations.RollbackError as re:
                format_output(re.migrate_exc.output, False)
                log_status(migration, red('Rollback'))
                format_output(re.output, not re.exc)
                success = False
            except migrations.MigrationError as me:
                format_output(me.output, False, traceback=me.traceback)
                success = False
            else:
                format_output(output, True)
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
    migration = migrations.get(plugin_or_specs, filename)
    removed = migration.unrecord()
    if removed:
        log.info('Removed migration %s', migration.label)
    else:
        log.error('Migration not found %s', migration.label)


@grp.command()
@click.argument('plugin_or_specs')
@click.argument('filename', default=None, required=False, metavar='[FILENAME]')
def info(plugin_or_specs, filename):
    '''
    Display detailed info about a migration
    '''
    migration = migrations.get(plugin_or_specs, filename)
    log_status(migration, status_label(migration.record))
    try:
        echo(migration.module.__doc__)
    except migrations.MigrationError:
        echo(yellow('Module not found'))

    for op in migration.record.get('ops', []):
        display_op(op)


def display_op(op):
    timestamp = white(op['date'].strftime(DATE_FORMAT))
    label = white(op['type'].title()) + ' '
    echo('{label:.<70} [{date}]'.format(label=label, date=timestamp))
    format_output(op['output'], success=op['success'], traceback=op.get('traceback'))
