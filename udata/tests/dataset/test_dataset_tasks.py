import pytest

from udata.models import Dataset, Topic, CommunityResource
from udata.core.dataset import tasks
from udata.core.dataset.factories import DatasetFactory, CommunityResourceFactory
# Those imports seem mandatory for the csv adapters to be registered. This might be because of the decorator mechanism.
from udata.core.dataset.csv import DatasetCsvAdapter, ResourcesCsvAdapter, IssuesOrDiscussionCsvAdapter
from udata.core.organization.csv import OrganizationCsvAdapter
from udata.core.reuse.csv import ReuseCsvAdapter
from udata.core.tags.csv import TagCsvAdapter


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
    fs_filenames = [r.fs_filename for r in dataset.resources if r.url.endswith(r.fs_filename)]
    assert len(fs_filenames) == len(dataset.resources)
