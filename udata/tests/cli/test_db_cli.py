from datetime import datetime

import pytest

from udata.core.reuse.factories import ReuseFactory


@pytest.fixture
def migrations(db):
    db.migrations.insert_one(
        {
            "plugin": "udata",
            "filename": "test.py",
            "date": datetime.utcnow(),
            "script": 'print("ok")',
            "output": "ok",
        }
    )
    return db.migrations


def test_unrecord_with_complete_filename(cli, migrations):
    """Should display help without errors"""
    result = cli("db unrecord udata test.py")
    assert result.exit_code == 0
    assert migrations.count_documents({}) == 0


def test_unrecord_with_filename_without_extension(cli, migrations):
    """Should display help without errors"""
    result = cli("db unrecord udata test")
    assert result.exit_code == 0
    assert migrations.count_documents({}) == 0


def test_unrecord_with_single_parameter(cli, migrations):
    """Should display help without errors"""
    result = cli("db unrecord udata:test.py")
    assert result.exit_code == 0
    assert migrations.count_documents({}) == 0


def test_unrecord_with_single_parameter_without_extension(cli, migrations):
    """Should display help without errors"""
    result = cli("db unrecord udata:test")
    assert result.exit_code == 0
    assert migrations.count_documents({}) == 0


def test_unrecord_without_parameters(cli, migrations):
    """Should display help without errors"""
    result = cli("db unrecord", check=False)
    assert result.exit_code != 0
    assert migrations.count_documents({}) == 1


def test_unrecord_with_too_many_parameters(cli, migrations):
    """Should display help without errors"""
    result = cli("db unrecord udata test.py too many", check=False)
    assert result.exit_code != 0
    assert migrations.count_documents({}) == 1


def test_check_references_report_listfield_missing(cli, clean_db):
    reuse = ReuseFactory()
    # TODO: FIX... the following SHOULD wrongly unset the field instead of setting it to an empty list.
    # This is reproducible in an `udata shell` for example, but for some unknown reason, NOT reproducible
    # here in the tests...
    # reuse.datasets = []
    # reuse.save()
    # TODO: se we manually unset the field here, just to make sure the cli command `udata db check-integrity`
    # catches it.
    reuse.update(unset__datasets=True)
    result = cli("db check-integrity --models Reuse", check=False)
    assert "Reuse.datasets(Dataset) — list…: 1" in result.output
    assert result.exit_code != 0
