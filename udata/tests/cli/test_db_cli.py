from datetime import datetime

import pytest
from bson import ObjectId
from mongoengine.connection import get_db

from udata.models import Reuse
from udata.tests.api import PytestOnlyDBTestCase


@pytest.fixture
def migrations():
    get_db().migrations.insert_one(
        {
            "plugin": "udata",
            "filename": "test.py",
            "date": datetime.utcnow(),
            "script": 'print("ok")',
            "output": "ok",
        }
    )
    return get_db().migrations


class DBCliTest(PytestOnlyDBTestCase):
    def test_unrecord_with_complete_filename(self, cli, migrations):
        """Should display help without errors"""
        result = cli("db unrecord udata test.py")
        assert result.exit_code == 0
        assert migrations.count_documents({}) == 0

    def test_unrecord_with_filename_without_extension(self, cli, migrations):
        """Should display help without errors"""
        result = cli("db unrecord udata test")
        assert result.exit_code == 0
        assert migrations.count_documents({}) == 0

    def test_unrecord_with_single_parameter(self, cli, migrations):
        """Should display help without errors"""
        result = cli("db unrecord udata:test.py")
        assert result.exit_code == 0
        assert migrations.count_documents({}) == 0

    def test_unrecord_with_single_parameter_without_extension(self, cli, migrations):
        """Should display help without errors"""
        result = cli("db unrecord udata:test")
        assert result.exit_code == 0
        assert migrations.count_documents({}) == 0

    def test_unrecord_without_parameters(self, cli, migrations):
        """Should display help without errors"""
        result = cli("db unrecord", check=False)
        assert result.exit_code != 0
        assert migrations.count_documents({}) == 1

    def test_unrecord_with_too_many_parameters(self, cli, migrations):
        """Should display help without errors"""
        result = cli("db unrecord udata test.py too many", check=False)
        assert result.exit_code != 0
        assert migrations.count_documents({}) == 1

    def test_check_references_report_listfield_missing(self, cli):
        # The cli command `udata db check-integrity` should catch reuse object missing datasets field
        Reuse._get_collection().insert_one({"_id": ObjectId()})

        result = cli("db check-integrity --models Reuse", check=False)
        assert "Reuse.datasets(Dataset) — list…: 1" in result.output
        assert result.exit_code != 0
