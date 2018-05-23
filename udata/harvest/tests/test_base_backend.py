# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from datetime import datetime

from udata.utils import faker
from udata.core.dataset.factories import DatasetFactory
from udata.models import Dataset

from .factories import HarvestSourceFactory

from ..backends import BaseBackend, HarvestFilter


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
