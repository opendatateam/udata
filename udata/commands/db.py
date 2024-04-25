import collections
from itertools import groupby
import logging
import os
import traceback

import click
import mongoengine

from udata import migrations, models as core_models
from udata.api import oauth2 as oauth2_models
from udata.commands import cli, green, yellow, cyan, red, magenta, white, echo
from udata.harvest import models as harvest_models
from udata.mongo import db
from udata.notifications.mattermost import send_message


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

def check_references(models_to_check, fix = False):
    # Cannot modify local scope from Python… :-(
    class Log: content = ''

    def print_and_save(text):
        Log.content += text + '\n'
        print(text) 

    errors = collections.defaultdict(int)

    _models = []
    for models in core_models, harvest_models, oauth2_models:
        _models += [
            elt for _, elt in models.__dict__.items()
            if isinstance(elt, type) and issubclass(elt, (db.Document))
        ]

    references = []
    for model in set(_models):
        if model.__name__ == 'Activity':
            print(f'Skipping Activity model, scheduled for deprecation')
            continue
        if model.__name__ == 'GeoLevel':
            print(f'Skipping GeoLevel model, scheduled for deprecation')
            continue

        if models_to_check and model.__name__ not in models_to_check:
            continue

        # find "root" ReferenceField fields
        refs = [elt for elt in model._fields.values()
                if isinstance(elt, mongoengine.fields.ReferenceField)]
        references += [{
            'model': model,
            'repr': f'{model.__name__}.{r.name}',
            'name': r.name,
            'destination': r.document_type.__name__,
            'type': 'direct',
        } for r in refs]

        # find "root" GenericReferenceField
        refs = [elt for elt in model._fields.values()
                if isinstance(elt, mongoengine.fields.GenericReferenceField)]
        references += [{
            'model': model,
            'repr': f'{model.__name__}.{r.name}',
            'name': r.name,
            'destination': 'Generic',
            'type': 'direct',
        } for r in refs]

        # find ListField with ReferenceField
        list_fields = [elt for elt in model._fields.values()
                       if isinstance(elt, mongoengine.fields.ListField)]
        list_refs = [elt for elt in list_fields
                     if isinstance(elt.field, mongoengine.fields.ReferenceField)]
        references += [{
            'model': model,
            'repr': f'{model.__name__}.{lr.name}',
            'name': lr.name,
            'destination': lr.field.document_type.__name__,
            'type': 'list',
        } for lr in list_refs]

        # find ListField w/ EmbeddedDocumentField w/ ReferenceField
        list_embeds = [(elt, elt.field) for elt in list_fields
                       if isinstance(elt.field, mongoengine.fields.EmbeddedDocumentField)]
        for embed, embed_field in list_embeds:
            embed_refs = [elt for elt in embed_field.document_type_obj._fields.values()
                          if isinstance(elt, mongoengine.fields.ReferenceField)]
            references += [{
                'model': model,
                'repr': f'{model.__name__}.{embed.name}__{er.name}',
                'name': f'{embed.name}__{er.name}',
                'destination': er.document_type.__name__,
                'type': 'embed_list',
            } for er in embed_refs]

        # find EmbeddedDocumentField w/ ReferenceField
        embeds = [elt for elt in model._fields.values()
                  if isinstance(elt, mongoengine.fields.EmbeddedDocumentField)]
        for embed_field in embeds:
            embed_refs = [elt for elt in embed_field.document_type_obj._fields.values()
                          if isinstance(elt, mongoengine.fields.ReferenceField)]
            references += [{
                'model': model,
                'repr': f'{model.__name__}.{embed_field.name}__{er.name}',
                'name': f'{embed_field.name}__{er.name}',
                'destination': er.document_type.__name__,
                'type': 'embed',
            } for er in embed_refs]

        # find EmbeddedDocumentField w/ ListField w/ ReferenceField
        for embed_field in embeds:
            embed_lists = [elt for elt in embed_field.document_type_obj._fields.values()
                           if isinstance(elt, mongoengine.fields.ListField)]
            elists_refs = [elt for elt in embed_lists
                           if isinstance(elt.field, mongoengine.fields.ReferenceField)]
            references += [{
                'model': model,
                'repr': f'{model.__name__}.{embed_field.name}__{lr.name}',
                'name': f'{embed_field.name}__{lr.name}',
                'destination': lr.field.document_type.__name__,
                'type': 'embed_list_ref',
            } for lr in elists_refs]

    print_and_save('Those references will be inspected:')
    for reference in references:
        print_and_save(f'- {reference["repr"]}({reference["destination"]}) — {reference["type"]}')
    print_and_save('')

    total = 0
    for model, model_references in groupby(references, lambda i: i["model"]):
        model_references = list(model_references)
        count = model.objects.count()
        print_and_save(f'- doing {count} {model.__name__}…')
        errors[model] = {}

        qs = model.objects().no_cache().all()
        with click.progressbar(qs, length=count) as models:
            for obj in models:
                for reference in model_references:
                    key = f'\t- {reference["repr"]}({reference["destination"]}) — {reference["type"]}…'
                    if key not in errors[model]:
                        errors[model][key] = 0

                    try:
                        if reference['type'] == 'direct':
                            try:
                                _ = getattr(obj, reference['name'])
                            except mongoengine.errors.DoesNotExist:
                                errors[model][key] += 1
                                print(f'\t{model.__name__}#{obj.id} have a broken reference for `{reference["name"]}` (fixable with `--fix`)')
                                if fix:
                                    field = getattr(model, reference['name'])

                                    if field.reverse_delete_rule == db.NULLIFY:
                                        print(f"\t\t…fixing by setting to NULL (db.NULLIFY)")
                                        setattr(obj, reference['name'], None)
                                        obj.save()
                                    elif field.reverse_delete_rule == db.CASCADE:
                                        print(f"\t\t…fixing by deleting (db.CASCADE)")
                                        obj.delete()
                                    else:
                                        print(f"\t\tcannot fix because unknown `reverse_delete_rule` {field.reverse_delete_rule}")
                        elif reference['type'] == 'list':
                            to_remove = set()
                            attr_list = getattr(obj, reference['name'], [])
                            for i, sub in enumerate(attr_list):
                                try:
                                    _ = sub.id
                                except mongoengine.errors.DoesNotExist:
                                    errors[model][key] += 1
                                    print(f'\t{model.__name__}#{obj.id} have a broken reference for {reference["name"]}[{i}] (fixable with `--fix`)')
                                    to_remove.add(i)
                                    
                            if fix and len(to_remove) > 0:
                                print(f"\t\t…fixing the list by removing {len(to_remove)} elements")
                                attr_list[:] = [i for j, i in enumerate(attr_list) if j not in to_remove]
                                obj.save()
                        elif reference['type'] == 'embed_list':
                            p1, p2 = reference['name'].split('__')
                            attr_list = getattr(obj, p1, [])
                            to_remove = set()
                            for i, sub in enumerate(attr_list):
                                try:
                                    getattr(sub, p2)
                                except mongoengine.errors.DoesNotExist:
                                    errors[model][key] += 1
                                    to_remove.add(i)
                                    print(f'\t{model.__name__}#{obj.id} have a broken reference for {p1}[{i}].{p2} (fixable with `--fix`)')

                            if fix and len(to_remove) > 0:
                                print(f"\t\t…fixing the list by removing {len(to_remove)} elements")
                                attr_list[:] = [i for j, i in enumerate(attr_list) if j not in to_remove]
                                obj.save()
                        elif reference['type'] == 'embed':
                            p1, p2 = reference['name'].split('__')
                            sub = getattr(obj, p1)
                            if sub is None: continue
                            try:
                                getattr(sub, p2)
                            except mongoengine.errors.DoesNotExist:
                                errors[model][key] += 1
                                print(f'\t{model.__name__}#{obj.id} have a broken reference for {p1}.{p2}')
                        elif reference['type'] == 'embed_list_ref':
                            p1, p2 = reference['name'].split('__')
                            a = getattr(obj, p1)
                            if a is None: continue
                            sub = getattr(a, p2, [])
                            for i, child in enumerate(sub):
                                try:
                                    child.id
                                except mongoengine.errors.DoesNotExist:
                                    errors[model][key] += 1
                                    print(f'\t{model.__name__}#{obj.id} have a broken reference for {p1}.{p2}[{i}]')
                        else:
                            print_and_save(f'Unknown ref type {reference["type"]}')
                    except mongoengine.errors.FieldDoesNotExist as e:
                        print_and_save(f'[ERROR for {model.__name__} {obj.id}] {traceback.format_exc()}')

        for key, nb_errors in errors[model].items():
            print_and_save(f'{key}: {nb_errors}')
            total += nb_errors

    print_and_save(f'\n Total errors: {total}')

    if total > 0:
        send_message(Log.content)


@grp.command()
@click.option('--models', multiple=True, default=[], help='Model(s) to check')
@click.option('--fix', default=False, is_flag=True, help='Try to fix integrity problems')
def check_integrity(models, fix):
    '''Check the integrity of the database from a business perspective'''
    check_references(models, fix)
