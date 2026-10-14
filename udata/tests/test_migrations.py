from datetime import UTC, datetime
from pathlib import Path
from textwrap import dedent

import pytest
from mongoengine.connection import get_db

from udata.db import migrations
from udata.tests.api import PytestOnlyDBTestCase


class MigrationsCommandsTest(PytestOnlyDBTestCase):
    """Test migration commands without mocking, using real migration files"""

    @pytest.fixture
    def db(self):
        return get_db()

    @pytest.fixture
    def migration_file(self, tmp_path):
        """Create a temporary migration file in udata/migrations"""
        migrations_dir = Path(__file__).parent.parent / "migrations"
        migration_path = migrations_dir / "test_migration_temp.py"

        # Create a simple migration
        migration_content = dedent(
            """\
            '''Test migration for integration testing'''
            import logging

            log = logging.getLogger(__name__)

            def migrate(db):
                db.test_collection.insert_one({'test': 'value'})
                log.info('Migration executed successfully')
            """
        )
        migration_path.write_text(migration_content)

        yield "test_migration_temp.py"

        # Cleanup
        if migration_path.exists():
            migration_path.unlink()

    @pytest.fixture
    def failing_migration(self, db):
        """A migration that always fails, and one scheduled after it.

        Named so that they sort last, leaving the real migrations to run normally first.
        """
        migrations_dir = Path(__file__).parent.parent / "migrations"
        failing = migrations_dir / "9999-01-01-failing-migration-temp.py"
        following = migrations_dir / "9999-01-02-following-migration-temp.py"
        failing.write_text(
            dedent(
                """\
                '''A migration that fails'''

                def migrate(db):
                    raise KeyError("something the data did not have")
                """
            )
        )
        following.write_text(
            dedent(
                """\
                '''The migration scheduled right after the failing one'''

                def migrate(db):
                    db.test_collection.insert_one({'test': 'value'})
                """
            )
        )

        yield failing.name, following.name

        failing.unlink()
        following.unlink()
        db.migrations.delete_many({"filename": {"$in": [failing.name, following.name]}})
        db.test_collection.delete_many({})

    def test_migrate_exits_with_an_error_when_a_migration_fails(self, db, failing_migration):
        """Otherwise the deployment that ran it carries on over an unmigrated database."""
        result = self.cli("db migrate", expect_error=True)

        assert result.exit_code != 0

    def test_a_failed_migration_holds_back_the_ones_after_it(self, db, failing_migration):
        """Running them out of order would apply transformations the failed one had to make
        first, so they wait — which is exactly why the command has to report a failure."""
        failing, following = failing_migration

        self.cli("db migrate", expect_error=True)

        assert db.migrations.find_one({"filename": failing})["ops"][-1]["success"] is False
        assert db.migrations.find_one({"filename": following}) is None
        assert db.test_collection.find_one() is None

    def test_list_available_migrations(self):
        """Test that we can list available migrations"""
        result = self.cli("db status")
        assert result.exit_code == 0
        # Should contain at least some output (may be empty if no migrations)

    def test_migration_workflow(self, db, migration_file):
        """Test complete migration workflow: info, migrate, status, unrecord"""

        # 1. Test info command on non-executed migration
        result = self.cli(f"db info {migration_file}")
        assert result.exit_code == 0
        assert "Test migration for integration testing" in result.output
        assert "Not applied" in result.output

        # 2. Test migrate command
        result = self.cli("db migrate")
        assert result.exit_code == 0

        # Verify migration was executed
        inserted = db.test_collection.find_one()
        assert inserted is not None
        assert inserted["test"] == "value"

        # Verify migration was recorded
        record = db.migrations.find_one({"filename": migration_file})
        assert record is not None
        assert record["filename"] == migration_file
        assert len(record["ops"]) == 1
        assert record["ops"][0]["type"] == "migrate"
        assert record["ops"][0]["success"] is True

        # 3. Test status command after migration
        result = self.cli("db status")
        assert result.exit_code == 0
        assert migration_file.replace(".py", "") in result.output

        # 4. Test info command on executed migration
        result = self.cli(f"db info {migration_file}")
        assert result.exit_code == 0
        assert "Test migration for integration testing" in result.output

        # 5. Test unrecord command
        result = self.cli(f"db unrecord {migration_file}")
        assert result.exit_code == 0

        # Verify migration record was removed
        record = db.migrations.find_one({"filename": migration_file})
        assert record is None

        # But data inserted by migration should still be there
        inserted = db.test_collection.find_one()
        assert inserted is not None
        assert inserted["test"] == "value"

        # Cleanup test data
        db.test_collection.delete_many({})

    def test_migrate_recordonly(self, db, migration_file):
        """Test migrate with --record flag"""

        result = self.cli("db migrate --record")
        assert result.exit_code == 0

        # Migration should be recorded
        record = db.migrations.find_one({"filename": migration_file})
        assert record is not None
        assert record["ops"][0]["output"] == [["info", "Recorded only"]]

        # But data should NOT be inserted
        inserted = db.test_collection.find_one()
        assert inserted is None

        # Cleanup
        db.migrations.delete_one({"filename": migration_file})

    def test_migrate_dry_run(self, db, migration_file):
        """Test migrate with --dry-run flag"""

        result = self.cli("db migrate --dry-run")
        assert result.exit_code == 0

        # Migration should NOT be recorded
        record = db.migrations.find_one({"filename": migration_file})
        assert record is None

        # Data should NOT be inserted
        inserted = db.test_collection.find_one()
        assert inserted is None

    def test_migrate_already_applied(self, db, migration_file):
        """Test that already applied migrations are skipped"""

        # First migration
        result = self.cli("db migrate")
        assert result.exit_code == 0

        # Count records
        count_before = db.test_collection.count_documents({})

        # Second migration attempt
        result = self.cli("db migrate")
        assert result.exit_code == 0
        assert "Skipped" in result.output

        # No new records should be inserted
        count_after = db.test_collection.count_documents({})
        assert count_before == count_after

        # Cleanup
        db.test_collection.delete_many({})
        db.migrations.delete_one({"filename": migration_file})

    def test_unrecord_with_complete_filename(self, db):
        """Should unrecord migration with complete filename"""
        db.migrations.insert_one(
            {
                "filename": "test.py",
                "ops": [
                    {
                        "date": datetime.now(UTC),
                        "type": "migrate",
                        "script": 'print("ok")',
                        "output": "ok",
                        "success": True,
                    }
                ],
            }
        )
        result = self.cli("db unrecord test.py")
        assert result.exit_code == 0
        assert db.migrations.count_documents({}) == 0

    def test_unrecord_without_parameters(self, db):
        """Should fail when no filename is provided"""
        db.migrations.insert_one(
            {
                "filename": "test.py",
                "ops": [
                    {
                        "date": datetime.now(UTC),
                        "type": "migrate",
                        "script": 'print("ok")',
                        "output": "ok",
                        "success": True,
                    }
                ],
            }
        )
        result = self.cli("db unrecord", expect_error=True)
        assert result.exit_code != 0
        assert db.migrations.count_documents({}) == 1

    def test_all_existing_migrations_can_run(self, db):
        """Test that all existing migrations can be executed without errors on a clean database"""
        # Get all available migrations
        all_migrations = migrations.list_available()

        # Run migrations
        result = self.cli("db migrate")
        assert result.exit_code == 0

        # Verify all migrations were recorded successfully
        for migration in all_migrations:
            record = db.migrations.find_one({"filename": migration.filename})
            assert record is not None, f"Migration {migration.filename} was not recorded"
            assert len(record["ops"]) > 0, f"Migration {migration.filename} has no operations"

            last_op = record["ops"][-1]
            assert last_op["success"], (
                f"Migration {migration.filename} failed: {last_op.get('output', 'No output')}"
            )
            assert last_op["type"] == "migrate", (
                f"Migration {migration.filename} last op is not migrate"
            )
