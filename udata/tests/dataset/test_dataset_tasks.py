# -*- coding: utf-8 -*-

import pytest

from udata.models import Dataset, Topic
from udata.core.dataset import tasks
from udata.core.organization.factories import OrganizationFactory
# csv.adapter for Tag won't be registered if this is not imported :thinking:
from udata.core.tags import csv as _  # noqa


pytestmark = pytest.mark.usefixtures('clean_db')


def test_purge_datasets():
    datasets = [
        Dataset.objects.create(title='delete me', deleted='2016-01-01'),
        Dataset.objects.create(title='keep me'),
    ]

    topic = Topic.objects.create(name='test topic', datasets=datasets)
    tasks.purge_datasets()

    topic = Topic.objects(name='test topic').first()
    assert topic.datasets[0] == datasets[1]


@pytest.mark.usefixtures('instance_path')
def test_export_csv(app):
    organization = OrganizationFactory()
    app.config['EXPORT_CSV_DATASET_INFO']['organization'] = organization.id
    slug = app.config['EXPORT_CSV_DATASET_INFO']['slug']
    models = app.config['EXPORT_CSV_MODELS']
    tasks.export_csv()
    dataset = Dataset.objects.get(slug=slug)
    assert dataset is not None
    assert dataset.organization == organization
    assert len(dataset.resources) == len(models)
    extras = [r.extras.get('csv-export:model') for r in dataset.resources]
    for model in models:
        assert model in extras
