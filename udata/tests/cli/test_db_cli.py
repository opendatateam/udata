from datetime import datetime

from bson import ObjectId
import pytest

from udata.core.dataset.factories import DatasetFactory
from udata.mongo import db
from udata.commands.db import check_references
from udata.harvest.models import HarvestItem, HarvestJob, HarvestSource
from udata.harvest.tests.factories import HarvestJobFactory
from udata.tests.api import APITestCase


@pytest.fixture
def migrations(db):
    db.migrations.insert_one({
        'plugin': 'udata',
        'filename': 'test.py',
        'date': datetime.utcnow(),
        'script': 'print("ok")',
        'output': 'ok',
    })
    return db.migrations


def test_unrecord_with_complete_filename(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord udata test.py')
    assert result.exit_code == 0
    assert migrations.count_documents({}) == 0


def test_unrecord_with_filename_without_extension(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord udata test')
    assert result.exit_code == 0
    assert migrations.count_documents({}) == 0


def test_unrecord_with_single_parameter(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord udata:test.py')
    assert result.exit_code == 0
    assert migrations.count_documents({}) == 0


def test_unrecord_with_single_parameter_without_extension(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord udata:test')
    assert result.exit_code == 0
    assert migrations.count_documents({}) == 0


def test_unrecord_without_parameters(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord', check=False)
    assert result.exit_code != 0
    assert migrations.count_documents({}) == 1


def test_unrecord_with_too_many_parameters(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord udata test.py too many', check=False)
    assert result.exit_code != 0
    assert migrations.count_documents({}) == 1
