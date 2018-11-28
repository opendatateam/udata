'''
Data migrations logic
'''
import importlib.util
import inspect
import logging
import os
import queue

from datetime import datetime
from logging.handlers import QueueHandler
from flask import current_app
from mongoengine.connection import get_db
from pkg_resources import resource_isdir, resource_listdir, resource_filename, resource_string

from udata import entrypoints

log = logging.getLogger(__name__)


class MigrationError(Exception):
    '''
    Raised on migration execution error.

    :param msg str: A human readable message (a reason)
    :param output str: An optionnal array of logging output
    :param exc Exception: An optionnal underlying exception
    '''
    def __init__(self, msg, output=None, exc=None):
        super().__init__(msg)
        self.msg = msg
        self.output = output
        self.exc = exc


class RollbackError(MigrationError):
    '''
    Raised on rollback.
    Hold the initial migration error and rollback exception (if any)
    '''
    def __init__(self, msg, output=None, exc=None, migrate_exc=None):
        super().__init__(msg)
        self.msg = msg
        self.output = output
        self.exc = exc
        self.migrate_exc = migrate_exc


class MigrationFormatter(logging.Formatter):
    pass


def get_record(plugin, filename):
    '''Get an existing migration record if exists'''
    return get_db().migrations.find_one({'plugin': plugin, 'filename': filename})


def record(plugin, filename, module_name=None, dryrun=False):
    '''Only record a migration without applying it'''
    if get_record(plugin, filename):
        return False
    try:
        path = _migration_path(plugin, filename, module_name)
    except Exception:
        return False
    if not os.path.exists(path):
        return False
    get_db().migrations.insert_one({
        'plugin': plugin,
        'filename': filename,
        'date': datetime.now(),
        # 'script': migration.script,
        # 'output': 'Recorded only'
    })
    return True


def unrecord(plugin, filename):
    '''Only record a migration without applying it'''
    record = get_record(plugin, filename)
    if record is None:
        return False
    get_db().migrations.delete_one({'_id': record['_id']})
    return True


def list_availables():
    '''
    List available migrations for udata and enabled plugins

    Each row is tuple with following signature:

        (plugin, package, filename)
    '''
    migrations = []

    migrations.extend(_iter('udata', 'udata'))

    plugins = entrypoints.get_enabled('udata.models', current_app)
    for plugin, module in plugins.items():
        migrations.extend(_iter(plugin, module))
    return sorted(migrations, key=lambda r: r[2])


def execute(plugin, filename, module_name=None, recordonly=False, dryrun=False):
    '''
    Execute a migration given a plugin (and optionnaly its resolved module name) and a filename

    If recordonly is True, the migration is only recorded
    If dryrun is True, the migration is neither executed nor recorded
    '''
    migration = _load_migration(plugin, filename, module_name)

    q = queue.Queue(-1)  # no limit on size
    handler = QueueHandler(q)
    handler.setFormatter(MigrationFormatter())
    logger = getattr(migration, 'log', logging.getLogger(migration.__name__))
    logger.propagate = False
    for h in logger.handlers:
        logger.removeHandler(h)
    logger.addHandler(handler)

    if not hasattr(migration, 'migrate'):
        error = SyntaxError('A migration should at least have a migrate(db) function')
        raise MigrationError('Error while executing migration', exc=error)

    if not recordonly and not dryrun:
        db = get_db()
        db._state = {}
        try:
            migration.migrate(db)
        except Exception as e:
            fe = MigrationError('Error while executing migration',
                                output=_extract_output(q), exc=e)
            if hasattr(migration, 'rollback'):
                try:
                    migration.rollback(db)
                except Exception as re:
                    raise MigrationError('Error while executing migration rollback',
                                         output=_extract_output(q), exc=re)
            raise fe
        
    if not dryrun:
        record(plugin, filename)

    return _extract_output(q)


def _iter(plugin, module):
    '''
    Iter over migrations for a given plugin module

    Yield tuples in the form (plugin_name, module_name, filename)
    '''
    module_name = module if isinstance(module, str) else module.__name__
    if not resource_isdir(module_name, 'migrations'):
        return
    for filename in resource_listdir(module_name, 'migrations'):
        if filename.endswith('.py') and not filename.startswith('__'):
            yield (plugin, module_name, filename)


def _module_name(plugin):
    '''Get the module namefor a given plugin'''
    if plugin == 'udata':
        return 'udata'
    module = entrypoints.get_plugin_module('udata.models', current_app, plugin)
    if module is None:
        raise ValueError('Plugin {} not found'.format(plugin))
    return module.__name__


def _migration_path(plugin, filename, module_name=None):
    '''Get a migration file path'''
    module_name = module_name or _module_name(plugin)
    filename = os.path.join('migrations', filename)
    return resource_filename(module_name, filename)


def _load_migration(plugin, filename, module_name=None):
    '''
    Load a migration from its python file

    :returns: the loaded module
    '''
    module_name = module_name or _module_name(plugin)
    basename = os.path.splitext(os.path.basename(filename))[0]
    name = '.'.join((module_name, 'migrations', basename))
    filename = os.path.join('migrations', filename)
    script = resource_string(module_name, filename)
    spec = importlib.util.spec_from_loader(name, loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(script, module.__dict__)
    return module


def _extract_output(q):
    '''Extract log output from a QueueHandler queue'''
    out = []
    while not q.empty():
        record = q.get()
        out.append((record.levelname.lower(), record.getMessage()))
    return out
