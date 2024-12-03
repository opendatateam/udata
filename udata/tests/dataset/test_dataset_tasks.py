import pytest

# Those imports seem mandatory for the csv adapters to be registered.
# This might be because of the decorator mechanism.
from udata.core.dataservices.models import Dataservice
from udata.core.dataset import tasks
from udata.core.dataset.csv import DatasetCsvAdapter, ResourcesCsvAdapter  # noqa
from udata.core.dataset.factories import CommunityResourceFactory, DatasetFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.organization.csv import OrganizationCsvAdapter  # noqa
from udata.core.reuse.csv import ReuseCsvAdapter  # noqa
from udata.core.tags.csv import TagCsvAdapter  # noqa
from udata.core.user.factories import UserFactory
from udata.harvest.csv import HarvestSourceCsvAdapter  # noqa
from udata.harvest.models import HarvestItem, HarvestJob
from udata.harvest.tests.factories import HarvestJobFactory
from udata.models import CommunityResource, Dataset, Discussion, Follow, Topic, Transfer

pytestmark = pytest.mark.usefixtures("clean_db")


def test_purge_datasets():
    datasets = [
        Dataset.objects.create(title="delete me", deleted="2016-01-01"),
        Dataset.objects.create(title="keep me"),
    ]

    topic = Topic.objects.create(name="test topic", datasets=datasets)

    user = UserFactory()
    transfer = Transfer.objects.create(
        owner=user,
        recipient=user,
        subject=datasets[0],
        comment="comment",
    )

    discussion = DiscussionFactory(subject=datasets[0])

    follower = Follow.objects.create(follower=user, following=datasets[0])

    HarvestJobFactory(items=[HarvestItem(dataset=datasets[0])])

    Dataservice.objects.create(title="test", datasets=datasets)

    tasks.purge_datasets()

    assert Transfer.objects.filter(id=transfer.id).count() == 0

    topic = Topic.objects(name="test topic").first()
    assert topic.datasets[0] == datasets[1]

    assert Discussion.objects.filter(id=discussion.id).count() == 0
    assert Follow.objects.filter(id=follower.id).count() == 0
    assert HarvestJob.objects.filter(items__dataset=datasets[0].id).count() == 0
    assert Dataservice.objects.filter(datasets=datasets[0].id).count() == 0


def test_purge_datasets_community():
    dataset = Dataset.objects.create(title="delete me", deleted="2016-01-01")
    community_resource1 = CommunityResourceFactory()
    community_resource1.dataset = dataset
    community_resource1.save()

    tasks.purge_datasets()
    assert CommunityResource.objects.count() == 0


@pytest.mark.usefixtures("instance_path")
def test_export_csv(app):
    dataset = DatasetFactory()
    app.config["EXPORT_CSV_DATASET_ID"] = dataset.id
    models = app.config["EXPORT_CSV_MODELS"]
    tasks.export_csv()
    dataset = Dataset.objects.get(id=dataset.id)
    assert len(dataset.resources) == len(models)
    extras = [r.extras.get("csv-export:model") for r in dataset.resources]
    for model in models:
        assert model in extras
    fs_filenames = [r.fs_filename for r in dataset.resources if r.url.endswith(r.fs_filename)]
    assert len(fs_filenames) == len(dataset.resources)
