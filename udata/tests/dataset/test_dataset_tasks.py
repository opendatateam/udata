import pytest

from udata.models import Dataset, Topic, CommunityResource
from udata.core.dataset import tasks
from udata.core.dataset.factories import DatasetFactory, CommunityResourceFactory
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


def test_purge_datasets_community():
    dataset = Dataset.objects.create(title='delete me', deleted='2016-01-01')
    community_resource1 = CommunityResourceFactory()
    community_resource1.dataset = dataset
    community_resource1.save()

    tasks.purge_datasets()
    assert CommunityResource.objects.count() == 0


def test_purge_orphan_community():
    dataset = Dataset.objects.create(title='test_dataset')
    community_resource1 = CommunityResourceFactory(title='test_community_1')
    community_resource2 = CommunityResourceFactory(title='test_community_2')
    community_resource1.dataset = dataset
    community_resource1.save()

    tasks.purge_orphan_community_resources()
    assert CommunityResource.objects.count() == 1


@pytest.mark.usefixtures('instance_path')
def test_export_csv(app):
    dataset = DatasetFactory()
    app.config['EXPORT_CSV_DATASET_ID'] = dataset.id
    models = app.config['EXPORT_CSV_MODELS']
    tasks.export_csv()
    dataset = Dataset.objects.get(id=dataset.id)
    assert len(dataset.resources) == len(models)
    extras = [r.extras.get('csv-export:model') for r in dataset.resources]
    for model in models:
        assert model in extras
