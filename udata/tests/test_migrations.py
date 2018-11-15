import importlib.util
import pytest

from datetime import datetime

from udata.migrations import manager
from udata.tests.helpers import assert_equal_dates


class MigrationsMock:
    def __init__(self, root):
        self.root = root
        self.plugins = set()
        self.enabled = set()
        self.build_module('udata')

    def add_migration(self, plugin, filename, content, enable=True):
        module = self.ensure_plugin(plugin, enabled=enable)
        module.ensure_dir('migrations')
        migration = module / 'migrations' / filename
        migration.write(content)

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
        # root = self.core if name == 'udata' else (self.root / name)
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


@pytest.fixture
def mock(tmpdir, mocker):
    '''
    Mock migrations files
    '''
    m = MigrationsMock(tmpdir)
    mocker.patch('udata.migrations.resource_listdir', side_effect=m.mock_resource_listdir)
    mocker.patch('udata.migrations.resource_isdir', side_effect=m.mock_resource_isdir)
    mocker.patch('udata.migrations.resource_string', side_effect=m.mock_resource_string)
    mocker.patch('udata.migrations.resource_filename', side_effect=m.mock_resource_filename)
    mocker.patch('udata.entrypoints.get_enabled', side_effect=m.mock_get_enabled_entrypoints)
    yield m


@pytest.mark.usefixtures('app')
class MigrationManagerTest:
    def test_list_available_migrations(self, mock):
        mock.add_migration('udata', '01_core_migration.py', '')
        mock.add_migration('test', '02_test_migration.py', '')
        mock.add_migration('other', '03_other_migration.py', '')
        # Should not list `__*.py` files
        mock.add_migration('test', '__private.py', '')
        # Should not list migrations for disabled plugin
        mock.add_migration('disabled', 'should_not_be_there.py', '', enable=False)
        # Should not fail on plugins without migrations dir
        mock.ensure_plugin('nomigrations')

        migrations = manager.available_migrations()

        assert len(migrations) == 3
        assert migrations == [
            ('udata', 'udata', '01_core_migration.py'),
            ('test', 'test', '02_test_migration.py'),
            ('other', 'other', '03_other_migration.py'),
        ]

    def test_get_migration(self, db):
        inserted = {
            'plugin': 'test',
            'filename': 'filename.py',
            'date': datetime.now(),
            'script': 'script',
            'output': 'output',
        }
        db.migrations.insert_one(inserted)

        migration = manager.get_migration('test', 'filename.py')

        assert migration['plugin'] == inserted['plugin']
        assert migration['filename'] == inserted['filename']
        assert migration['script'] == inserted['script']
        assert migration['output'] == inserted['output']
        assert_equal_dates(migration['date'], inserted['date'])

    def test_get_migration_not_found(self, clean_db):
        assert manager.get_migration('test', 'filename.py') is None

    def test_record_migration(self, mock, db):
        mock.add_migration('test', 'filename.py', '# whatever')

        assert manager.record_migration('test', 'filename.py')

        migration = db.migrations.find_one()
        assert migration['plugin'] == 'test'
        assert migration['filename'] == 'filename.py'
        assert migration['script'] == '# whatever'
        assert migration['output'] == 'Recorded only'

    def test_record_missing_migration(self, db):
        assert not manager.record_migration('test', 'filename.py')
        assert db.migrations.find_one() is None

    def test_unrecord_migration(self, db):
        inserted = {
            'plugin': 'test',
            'filename': 'filename.py',
            'date': datetime.now(),
            'script': 'script',
            'output': 'output',
        }
        db.migrations.insert_one(inserted)

        # Remove the migration record, return True
        assert manager.unrecord_migration('test', 'filename.py')
        assert db.migrations.find_one() is None
        # Already removed, return False
        assert not manager.unrecord_migration('test', 'filename.py')

    # def test_execute_migration(self, mock):
    #     mock.add_core_migration('01_core_migration.py', '')
    #     mock.add_migration('test', '02_test_migration.py', '')
    #     mock.add_migration('other', '03_other_migration.py', '')
    #     # Should not list `__*.py` files
    #     mock.add_migration('test', '__private.py', '')
    #     # Should not list migrations for disabled plugin
    #     mock.add_migration('disabled', 'should_not_be_there.py', '', enable=False)
    #     # Should not fail on plugins without migrations dir
    #     mock.ensure_plugin('nomigrations')

    #     migrations = manager.available_migrations()

    #     assert len(migrations) == 3
    #     assert migrations == [
    #         ('udata', 'udata', '01_core_migration.py'),
    #         ('test', 'test', '02_test_migration.py'),
    #         ('other', 'other', '03_other_migration.py'),
    #     ]
