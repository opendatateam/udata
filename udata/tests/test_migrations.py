import importlib.util
import pytest

from datetime import datetime
from textwrap import dedent

from udata import migrations
from udata.tests.helpers import assert_equal_dates


class MigrationsMock:
    def __init__(self, root):
        self.root = root
        self.plugins = set()
        self.enabled = set()
        self.build_module('udata')

    def add_migration(self, plugin, filename, content='', enable=True):
        module = self.ensure_plugin(plugin, enabled=enable)
        module.ensure_dir('migrations')
        migration = module / 'migrations' / filename
        migration.write(dedent(content))

    def build_module(self, name):
        root = self.root.ensure_dir(name)
        root.ensure('__init__.py')

    def ensure_plugin(self, plugin, enabled=True):
        if plugin not in self.plugins and plugin != 'udata':
            self.build_module(plugin)
            self.plugins.add(plugin)
        if enabled and plugin != 'udata':
            self.enabled.add(plugin)
        else:
            self.enabled.discard(plugin)
        return self.root / plugin

    def _load_module(self, name, path):
        # See: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
        spec = importlib.util.spec_from_file_location(name, str(path / '__init__.py'))
        module = importlib.util.module_from_spec(spec)
        return module

    def _resource_path(self, name, path):
        return self.root / name / path

    def mock_resource_listdir(self, name, dirname):
        target = self._resource_path(name, dirname)
        return [f.relto(target) for f in target.listdir()]

    def mock_resource_string(self, name, filename):
        target = self._resource_path(name, filename)
        return target.read()

    def mock_resource_filename(self, name, filename):
        return str(self._resource_path(name, filename))

    def mock_resource_isdir(self, name, dirname):
        return self._resource_path(name, dirname).check(dir=1, exists=1)

    def mock_get_enabled_entrypoints(self, entrypoint, app):
        return {
            plugin: self._load_module(plugin, self.root / plugin)
            for plugin in self.enabled
        }

    def mock_get_plugin_module(self, entrypoint, app, plugin):
        return self._load_module(plugin, self.root / plugin)


@pytest.fixture
def mock(app, tmpdir, mocker):
    '''
    Mock migrations files
    '''
    m = MigrationsMock(tmpdir)
    mocker.patch('udata.migrations.resource_listdir', side_effect=m.mock_resource_listdir)
    mocker.patch('udata.migrations.resource_isdir', side_effect=m.mock_resource_isdir)
    mocker.patch('udata.migrations.resource_string', side_effect=m.mock_resource_string)
    mocker.patch('udata.migrations.resource_filename', side_effect=m.mock_resource_filename)
    mocker.patch('udata.entrypoints.get_enabled', side_effect=m.mock_get_enabled_entrypoints)
    mocker.patch('udata.entrypoints.get_plugin_module', side_effect=m.mock_get_plugin_module)
    yield m


def test_list_available_migrations(mock):
    mock.add_migration('udata', '01_core_migration.py')
    mock.add_migration('test', '02_test_migration.py')
    mock.add_migration('other', '03_other_migration.py')
    # Should not list `__*.py` files
    mock.add_migration('test', '__private.py')
    # Should not list migrations for disabled plugin
    mock.add_migration('disabled', 'should_not_be_there.py', enable=False)
    # Should not fail on plugins without migrations dir
    mock.ensure_plugin('nomigrations')

    availables = migrations.list_availables()

    assert len(availables) == 3
    assert availables == [
        ('udata', 'udata', '01_core_migration.py'),
        ('test', 'test', '02_test_migration.py'),
        ('other', 'other', '03_other_migration.py'),
    ]


def test_get_record(db):
    inserted = {
        'plugin': 'test',
        'filename': 'filename.py',
        'date': datetime.now(),
        # 'script': 'script',
        # 'output': 'output',
    }
    db.migrations.insert_one(inserted)

    record = migrations.get_record('test', 'filename.py')

    assert record['plugin'] == inserted['plugin']
    assert record['filename'] == inserted['filename']
    # assert record['script'] == inserted['script']
    # assert record['output'] == inserted['output']
    assert_equal_dates(record['date'], inserted['date'])


def test_record_migration(mock, db):
    mock.add_migration('test', 'filename.py', '# whatever')

    assert migrations.record('test', 'filename.py')

    migration = db.migrations.find_one()
    assert migration['plugin'] == 'test'
    assert migration['filename'] == 'filename.py'
    # assert migration['script'] == '# whatever'
    # assert migration['output'] == 'Recorded only'


def test_record_missing_plugin(db):
    assert not migrations.record('test', 'filename.py')
    assert db.migrations.find_one() is None


def test_record_missing_migration(db, mock):
    mock.ensure_plugin('test')
    assert not migrations.record('test', 'filename.py')
    assert db.migrations.find_one() is None


def test_unrecord_migration(db):
    inserted = {
        'plugin': 'test',
        'filename': 'filename.py',
        'date': datetime.now(),
        # 'script': 'script',
        # 'output': 'output',
    }
    db.migrations.insert_one(inserted)

    # Remove the migration record, return True
    assert migrations.unrecord('test', 'filename.py')
    assert db.migrations.find_one() is None
    # Already removed, return False
    assert not migrations.unrecord('test', 'filename.py')


def test_execute_migration(mock, db):
    mock.add_migration('udata', 'migration.py', '''\
    import logging

    log = logging.getLogger(__name__)

    def migrate(db):
        db.test.insert_one({'key': 'value'})
        log.info('test')
    ''')

    output = migrations.execute('udata', 'migration.py')

    db.migrations.count_documents({}) == 1
    inserted = db.test.find_one()
    assert inserted is not None
    assert inserted['key'] == 'value'
    assert output == [
        ('info', 'test')
    ]


def test_execute_migration_error(mock, db):
    mock.add_migration('udata', 'migration.py', '''\
    import logging

    log = logging.getLogger(__name__)

    def migrate(db):
        db.test.insert_one({'key': 'value'})
        log.info('test')
        raise ValueError('error')
    ''')

    with pytest.raises(migrations.MigrationError) as excinfo:
        migrations.execute('udata', 'migration.py')

    exc = excinfo.value
    assert isinstance(exc, migrations.MigrationError)
    assert isinstance(exc.exc, ValueError)
    assert exc.msg == "Error while executing migration"
    assert exc.output == [
        ('info', 'test')
    ]

    # Without rollback DB is left as it is
    db.migrations.count_documents({}) == 1
    inserted = db.test.find_one()
    assert inserted is not None
    assert inserted['key'] == 'value'


def test_execute_migration_error_with_rollback(mock, db):
    mock.add_migration('udata', 'migration.py', '''\
    def migrate(db):
        db.test.insert_one({'key': 'value'})
        raise ValueError('error')
    
    def rollback(db):
        db.rollback_test.insert_one({'key': 'value'})
    ''')

    with pytest.raises(migrations.MigrationError) as excinfo:
        migrations.execute('udata', 'migration.py')

    exc = excinfo.value
    assert isinstance(exc, migrations.RollbackError)
    assert exc.exc is None
    assert exc.msg == "Error while executing migration, rollback has been applyied"

    assert isinstance(exc.migrate_exc, migrations.MigrationError)
    assert isinstance(exc.migrate_exc.exc, ValueError)
    assert exc.migrate_exc.msg == "Error while executing migration"

    # DB is rollbacked if possible
    # Migrations should not be recorded
    db.migrations.count_documents({}) == 0
    # Migrate value is inserted
    db.test.count_documents({}) == 1
    # Rollback should not be recorded
    db.rollback_test.count_documents({}) == 1


def test_execute_migration_error_with_state_rollback(mock, db):
    mock.add_migration('udata', 'migration.py', '''\
    def migrate(db):
        db.test.insert_one({'key': 'first'})
        db._state['first'] = True
        raise ValueError('error')
        db.test.insert_two({'key': 'second'})
        db._state['second'] = True
    
    def rollback(db):
        if db._state.get('first', False):
            db.rollback_test.insert_one({'key': 'first'})
        if db._state.get('second', False):
            db.rollback_test.insert_one({'key': 'second'})
    ''')

    with pytest.raises(migrations.MigrationError) as excinfo:
        migrations.execute('udata', 'migration.py')

    exc = excinfo.value
    assert isinstance(exc, migrations.RollbackError)
    assert exc.exc is None
    assert exc.msg == "Error while executing migration, rollback has been applyied"

    assert isinstance(exc.migrate_exc, migrations.MigrationError)
    assert isinstance(exc.migrate_exc.exc, ValueError)
    assert exc.migrate_exc.msg == "Error while executing migration"

    # Migrations should not be recorded
    db.migrations.count_documents({}) == 0
    # Only the first value is inserted
    db.test.count_documents({}) == 1
    # Only the first rollback operation is executed
    db.rollback_test.count_documents({}) == 1


def test_execute_migration_error_with_rollback_error(mock, db):
    mock.add_migration('udata', 'migration.py', '''\
    def migrate(db):
        db.test.insert_one({'key': 'value'})
        raise ValueError('error')
    
    def rollback(db):
        db.rollback_test.insert_one({'key': 'value'})
        raise ValueError('error')
    ''')

    with pytest.raises(migrations.MigrationError) as excinfo:
        migrations.execute('udata', 'migration.py')

    exc = excinfo.value
    assert isinstance(exc, migrations.RollbackError)
    assert isinstance(exc.exc, ValueError)
    assert exc.msg == "Error while executing migration rollback"

    assert isinstance(exc.migrate_exc, migrations.MigrationError)
    assert isinstance(exc.migrate_exc.exc, ValueError)
    assert exc.migrate_exc.msg == "Error while executing migration"

    # DB is rollbacked if possible
    # Migrations should not be recorded
    db.migrations.count_documents({}) == 0
    # Migrate value is inserted
    db.test.count_documents({}) == 1
    # Rollback should not be recorded
    db.rollback_test.count_documents({}) == 1
