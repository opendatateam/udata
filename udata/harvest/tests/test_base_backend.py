# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from datetime import datetime
from urlparse import urlparse

from dateutil.parser import parse
from voluptuous import Schema

from udata.utils import faker
from udata.core.dataset.factories import DatasetFactory
from udata.models import Dataset
from udata.tests.helpers import assert_equal_dates

from .factories import HarvestSourceFactory

from ..backends import BaseBackend, HarvestFilter, HarvestFeature
from ..exceptions import HarvestException


class Unknown:
    pass


class FakeBackend(BaseBackend):
    filters = (
        HarvestFilter('First filter', 'first', basestring),
        HarvestFilter('Second filter', 'second', basestring),
    )
    features = (
        HarvestFeature('feature', 'A test feature'),
        HarvestFeature('enabled', 'A test feature enabled by default', default=True),
    )

    def initialize(self):
        for i in range(self.source.config.get('nb_datasets', 3)):
            self.add_item('fake-{0}'.format(i))

    def process(self, item):
        dataset = self.get_dataset(item.remote_id)
        for key, value in DatasetFactory.as_dict(visible=True).items():
            setattr(dataset, key, value)
        if self.source.config.get('last_modified'):
            dataset.last_modified = self.source.config['last_modified']
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
        now = datetime.now()
        nb_datasets = 3
        source = HarvestSourceFactory(config={'nb_datasets': nb_datasets})
        backend = FakeBackend(source)

        job = backend.harvest()

        assert len(job.items) == nb_datasets
        assert Dataset.objects.count() == nb_datasets
        for dataset in Dataset.objects():
            assert_equal_dates(dataset.last_modified, now)
            assert dataset.extras['harvest:source_id'] == str(source.id)
            assert dataset.extras['harvest:domain'] == source.domain
            assert dataset.extras['harvest:remote_id'].startswith('fake-')
            harvest_last_update = parse(dataset.extras['harvest:last_update'])
            assert_equal_dates(harvest_last_update, now)

    def test_has_feature_defaults(self):
        source = HarvestSourceFactory()
        backend = FakeBackend(source)

        assert not backend.has_feature('feature')
        assert backend.has_feature('enabled')

    def test_has_feature_defined(self):
        source = HarvestSourceFactory(config={
            'features': {
                'feature': True,
                'enabled': False,
            }
        })
        backend = FakeBackend(source)

        assert backend.has_feature('feature')
        assert not backend.has_feature('enabled')

    def test_has_feature_unkown(self):
        source = HarvestSourceFactory()
        backend = FakeBackend(source)

        with pytest.raises(HarvestException):
            backend.has_feature('unknown')

    def test_get_filters_empty(self):
        source = HarvestSourceFactory()
        backend = FakeBackend(source)

        assert backend.get_filters() == []

    def test_get_filters(self):
        source = HarvestSourceFactory(config={
            'filters': [
                {'key': 'second', 'value': ''},
                {'key': 'first', 'value': ''},
            ]
        })
        backend = FakeBackend(source)

        assert [f['key'] for f in backend.get_filters()] == ['second', 'first']

    def test_harvest_source_id(self):
        nb_datasets = 3
        source = HarvestSourceFactory(config={'nb_datasets': nb_datasets})
        backend = FakeBackend(source)

        job = backend.harvest()
        assert len(job.items) == nb_datasets

        source_url = faker.url()
        source.url = source_url
        source.save()

        job = backend.harvest()
        datasets = Dataset.objects()
        # no new datasets have been created
        assert len(datasets) == nb_datasets
        for dataset in datasets:
            assert dataset.extras['harvest:source_id'] == str(source.id)
            parsed = urlparse(source_url).netloc.split(':')[0]
            assert parsed == dataset.extras['harvest:domain']

    def test_dont_overwrite_last_modified(self, mocker):
        last_modified = faker.date_time_between(start_date='-30y', end_date='-1y')
        source = HarvestSourceFactory(config={'nb_datasets': 1, 'last_modified': last_modified})
        backend = FakeBackend(source)

        backend.harvest()

        dataset = Dataset.objects.first()

        assert dataset.last_modified == last_modified
        harvest_last_update = parse(dataset.extras['harvest:last_update'])
        assert_equal_dates(harvest_last_update, datetime.now())

    def test_dont_overwrite_last_modified_even_if_set_to_same(self, mocker):
        last_modified = faker.date_time_between(start_date='-30y', end_date='-1y')
        source = HarvestSourceFactory(config={'nb_datasets': 1, 'last_modified': last_modified})
        backend = FakeBackend(source)

        backend.harvest()
        backend.harvest()  # Harvest twice to test same last_modified

        dataset = Dataset.objects.first()

        assert dataset.last_modified == last_modified
        harvest_last_update = parse(dataset.extras['harvest:last_update'])
        assert_equal_dates(harvest_last_update, datetime.now())


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
