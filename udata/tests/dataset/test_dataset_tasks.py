# -*- coding: utf-8 -*-

from .. import TestCase, DBTestMixin

from udata.models import Dataset, Topic
from udata.core.dataset import tasks


class DatasetTasksTest(TestCase, DBTestMixin):
    def test_purge_datasets(self):
        datasets = [
            Dataset.objects.create(title='delete me', deleted='2016-01-01'),
            Dataset.objects.create(title='keep me'),
        ]

        topic = Topic.objects.create(name='test topic', datasets=datasets)
        tasks.purge_datasets()

        topic = Topic.objects(name='test topic').first()
        self.assertListEqual(topic.datasets, [datasets[1]])
