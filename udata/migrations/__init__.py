'''
Data migrations logic
'''
import importlib.util
import logging
import os

from datetime import datetime
from flask import current_app
from mongoengine.connection import get_db
from pkg_resources import resource_isdir, resource_listdir, resource_filename, resource_string

from udata import entrypoints

log = logging.getLogger(__name__)


def normalize_migration(plugin_or_specs, filename):
    if filename is None and ':' in plugin_or_specs:
        plugin, filename = plugin_or_specs.split(':')
    else:
        plugin = plugin_or_specs
    if not filename.endswith('.py'):
        filename += '.py'
    return plugin, filename


class MigrationLogger:
    '''
    Allows to live logging during migrations and later store logged output
    '''
    def __init__(self):
        self.logged = []

    def log(self, level, msg, *args, **kwargs):
        msg = msg.format(*args, **kwargs)
        log[level](msg)
        self.logged.append(level, msg)

    def debug(self, msg, *args, **kwargs):
        self.log('debug', msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log('debug', msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log('debug', msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log('debug', msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.log('exception', msg, *args, **kwargs)


class Migration:
    '''
    Wraps a single migration
    '''
    def __init__(self, plugin, filename, module=None):
        self.plugin = plugin
        self.module_name = module or self.get_module_name(plugin)
        self.filename = filename
        self.script = None
        self.module = None

    def get_module_name(self, plugin):
        if plugin == 'udata':
            return 'udata'
        module = entrypoints.get_plugin_module('udata.models', current_app, plugin)
        if module is None:
            raise ValueError('Plugin {} not found'.format(plugin))
        return module.__name__

    @property
    def db(self):
        return get_db()

    @property
    def path(self):
        path = os.path.join('migrations', self.filename)
        return resource_filename(self.module_name, path)

    def load(self):
        basename = os.path.basename(self.filename)
        name = ':'.join((self.plugin, basename))
        filename = os.path.join('migrations', self.filename)
        self.script = resource_string(self.module_name, filename)
        spec = importlib.util.spec_from_loader(name, loader=None)
        self.module = importlib.util.module_from_spec(spec)
        exec(self.script, self.module.__dict__)

    def execute(self):
        if self.script is None:
            self.load()

        if not hasattr(self.module, 'migrate'):
            raise SyntaxError('A migration should at least have a migrate(db, log) function')

        logger = MigrationLogger()
        self.module.migrate(self.db, logger)

    def exists(self):
        return os.path.exists(self.path)

    def get_record(self):
        return self.db.migrations.find_one({'plugin': self.plugin, 'filename': self.filename})

    def is_recorded(self):
        return bool(self.get_record())

    def status(self):
        record = self.get_record()
        if not record:
            return
        return record['date']


class MigrationManager:
    '''
    Manage all data migrations
    '''
    @property
    def db(self):
        return get_db()

    @property
    def migrations(self):
        return self.db.migrations

    def get_migration(self, plugin, filename):
        '''Get an existing migration record if exists'''
        return Migration(plugin, filename)
        # return self.migrations.find_one({'plugin': plugin, 'filename': filename})

    def execute_migration(self, plugin, filename, dryrun=False):
        '''Execute and record a migration'''
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

    # def load_migration(self, plugin, filename):
    #     '''Load a migration file if exists'''
    #     module = entrypoints.get_plugin_module('udata.models', current_app, plugin)
    #     if module is None:
    #         return
    #     migration = Migration(plugin, module.__name__, filename)
    #     if not migration.exists():
    #         return
    #     print('Load', plugin, filename)
    #     migration.load()
    #     print('Loaded')
    #     return migration

    def record_migration(self, plugin, filename, dryrun=False):
        '''Only record a migration without applying it'''
        try:
            migration = Migration(plugin, filename)
        except ValueError:
            return
        if not migration.exists():
            return
        migration.load()
        self.migrations.insert_one({
            'plugin': plugin,
            'filename': filename,
            'date': datetime.now(),
            'script': migration.script,
            'output': 'Recorded only'
        })
        return True

    def unrecord_migration(self, plugin, filename):
        '''Only record a migration without applying it'''
        migration = self.get_migration(plugin, filename)
        if migration is None:
            return False
        self.migrations.delete_one({'_id': migration['_id']})
        return True

    def iter_migrations(self, plugin, module):
        module_name = module if isinstance(module, str) else module.__name__
        if not resource_isdir(module_name, 'migrations'):
            return
        for filename in resource_listdir(module_name, 'migrations'):
            if filename.endswith('.py') and not filename.startswith('__'):
                migration = Migration(plugin, filename, module_name)
                yield (plugin, module_name, filename)

    def available_migrations(self):
        '''
        List available migrations for udata and enabled plugins

        Each row is tuple with following signature:

            (plugin, package, filename)
        '''
        migrations = []

        migrations.extend(self.iter_migrations('udata', 'udata'))

        plugins = entrypoints.get_enabled('udata.models', current_app)
        for plugin, module in plugins.items():
            migrations.extend(self.iter_migrations(plugin, module))
        return sorted(migrations, key=lambda r: r[2])


manager = MigrationManager()
