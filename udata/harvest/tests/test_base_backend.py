# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from datetime import datetime

from voluptuous import Schema

from udata.utils import faker
from udata.core.dataset.factories import DatasetFactory
from udata.models import Dataset

from .factories import HarvestSourceFactory

from ..backends import BaseBackend, HarvestFilter
from ..exceptions import HarvestException


class Unknown:
    pass


class FakeBackend(BaseBackend):
    def initialize(self):
        for i in range(self.source.config.get('nb_datasets', 3)):
            self.add_item('fake-{0}'.format(i))

    def process(self, item):
        dataset = self.get_dataset(item.remote_id)
        for key, value in DatasetFactory.as_dict(visible=True).items():
            setattr(dataset, key, value)
        return dataset


class HarvestFilterTest:
    @pytest.mark.parametrize('type,expected', HarvestFilter.TYPES.items())
    def test_type_ok(self, type, expected):
        label = faker.word()
        key = faker.word()
        description = faker.sentence()
        hf = HarvestFilter(label, key, type, description)
        assert hf.as_dict() == {
            'label': label,
            'key': key,
            'type': expected,
            'description': description,
        }

    @pytest.mark.parametrize('type', [dict, list, tuple, Unknown])
    def test_type_ko(self, type):
        with pytest.raises(TypeError):
            HarvestFilter(faker.word(), faker.word(), type, faker.sentence())


@pytest.mark.usefixtures('clean_db')
class BaseBackendTest:
    def test_simple_harvest(self):
        nb_datasets = 3
        source = HarvestSourceFactory(config={'nb_datasets': nb_datasets})
        backend = FakeBackend(source)

        job = backend.harvest()

        assert len(job.items) == nb_datasets
        assert Dataset.objects.count() == nb_datasets
        for dataset in Dataset.objects():
            assert dataset.extras['harvest:source_id'] == str(source.id)
            assert dataset.extras['harvest:domain'] == source.domain
            assert dataset.extras['harvest:remote_id'].startswith('fake-')
            datetime.strptime(dataset.extras['harvest:last_update'],
                              '%Y-%m-%dT%H:%M:%S.%f')


@pytest.mark.usefixtures('clean_db')
class BaseBackendValidateTest:
    @pytest.fixture
    def validate(self):
        return FakeBackend(HarvestSourceFactory()).validate

    def test_valid_data(self, validate):
        schema = Schema({'key': basestring})
        data = {'key': 'value'}
        assert validate(data, schema) == data

    def test_handle_basic_error(self, validate):
        schema = Schema({'bad-value': basestring})
        data = {'bad-value': 42}
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert '[bad-value] expected basestring: 42' in msg

    def test_handle_required_values(self, validate):
        schema = Schema({'missing': basestring}, required=True)
        data = {}
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert '[missing] required key not provided' in msg
        assert '[missing] required key not provided: None' not in msg

    def test_handle_multiple_errors_on_object(self, validate):
        schema = Schema({'bad-value': basestring, 'other-bad-value': int})
        data = {'bad-value': 42, 'other-bad-value': 'wrong'}
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert '[bad-value] expected basestring: 42' in msg
        assert '[other-bad-value] expected int: wrong' in msg

    def test_handle_multiple_error_on_nested_object(self, validate):
        schema = Schema({'nested': {
            'bad-value': basestring, 'other-bad-value': int
        }})
        data = {'nested': {'bad-value': 42, 'other-bad-value': 'wrong'}}
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert '[nested.bad-value] expected basestring: 42' in msg
        assert '[nested.other-bad-value] expected int: wrong' in msg

    def test_handle_multiple_error_on_nested_list(self, validate):
        schema = Schema({'nested': [
            {'bad-value': basestring, 'other-bad-value': int}
        ]})
        data = {'nested': [
            {'bad-value': 42, 'other-bad-value': 'wrong'},
        ]}
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert '[nested.0.bad-value] expected basestring: 42' in msg
        assert '[nested.0.other-bad-value] expected int: wrong' in msg

    # See: https://github.com/alecthomas/voluptuous/pull/330
    @pytest.mark.skip(reason='Not yet supported by Voluptuous')
    def test_handle_multiple_error_on_nested_list_items(self, validate):
        schema = Schema({'nested': [
            {'bad-value': basestring, 'other-bad-value': int}
        ]})
        data = {'nested': [
            {'bad-value': 42, 'other-bad-value': 'wrong'},
            {'bad-value': 43, 'other-bad-value': 'bad'},
        ]}
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert '[nested.0.bad-value] expected basestring: 42' in msg
        assert '[nested.0.other-bad-value] expected int: wrong' in msg
        assert '[nested.1.bad-value] expected basestring: 43' in msg
        assert '[nested.1.other-bad-value] expected int: bad' in msg
