# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import pytest

from udata.models import db

@pytest.fixture
def migrations(clean_db):
    migrations = db.connection.get_default_database().migrations
    migrations.insert({
        'plugin': 'udata',
        'filename': 'test.js',
        'date': datetime.now(),
        'script': 'print("ok")',
        'output': 'ok',
    })
    return migrations


def test_unrecord_with_complete_filename(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord udata test.js')
    assert result.exit_code == 0
    assert migrations.count() == 0


def test_unrecord_with_filename_without_extension(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord udata test')
    assert result.exit_code == 0
    assert migrations.count() == 0

def test_unrecord_with_single_parameter(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord udata:test.js')
    assert result.exit_code == 0
    assert migrations.count() == 0

def test_unrecord_with_single_parameter_without_extension(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord udata:test')
    assert result.exit_code == 0
    assert migrations.count() == 0

def test_unrecord_without_parameters(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord', check=False)
    assert result.exit_code != 0
    assert migrations.count() == 1

def test_unrecord_with_too_many_parameters(cli, migrations):
    '''Should display help without errors'''
    result = cli('db unrecord udata test.js too many', check=False)
    assert result.exit_code != 0
    assert migrations.count() == 1
