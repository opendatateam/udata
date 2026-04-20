import pytest

# Those imports seem mandatory for the csv adapters to be registered.
# This might be because of the decorator mechanism.
from udata.core.dataservices.models import Dataservice
from udata.core.dataset import tasks
from udata.core.dataset.csv import DatasetCsvAdapter, ResourcesCsvAdapter  # noqa
from udata.core.dataset.factories import CommunityResourceFactory, DatasetFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.core.edito_blocs.models import DatasetsListBloc
from udata.core.organization.csv import OrganizationCsvAdapter  # noqa
from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.reuse.csv import ReuseCsvAdapter  # noqa
from udata.core.site.factories import SiteFactory
from udata.core.site.models import Site
from udata.core.tags.csv import TagCsvAdapter  # noqa
from udata.core.topic.models import TopicElement
from udata.core.user.factories import UserFactory
from udata.harvest.csv import HarvestSourceCsvAdapter  # noqa
from udata.harvest.models import HarvestItem, HarvestJob
from udata.harvest.tests.factories import HarvestJobFactory
from udata.models import CommunityResource, Dataset, Discussion, Follow, Topic, Transfer
from udata.tests.api import PytestOnlyDBTestCase


class DatasetTasksTest(PytestOnlyDBTestCase):
    def test_purge_datasets(self):
        datasets = [
            Dataset.objects.create(title="delete me", deleted="2016-01-01"),
            Dataset.objects.create(title="keep me"),
        ]

        topic = Topic.objects.create(name="test topic")
        for d in datasets:
            topic_element = TopicElement(element=d, topic=topic)
            topic_element.save()

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
        topic_element = topic.elements.first()
        assert topic_element.element is None

        assert Discussion.objects.filter(id=discussion.id).count() == 0
        assert Follow.objects.filter(id=follower.id).count() == 0
        assert HarvestJob.objects.filter(items__dataset=datasets[0].id).count() == 0
        assert Dataservice.objects.filter(datasets=datasets[0].id).count() == 0

    def test_purge_datasets_cleans_all_harvest_items_references(self):
        """Test that purging datasets cleans all HarvestItem references in a job.

        The same dataset can appear multiple times in a job's items (e.g. if the
        harvest source has duplicates). The $ operator only updates the first match,
        so we need to use $[] with array_filters to update all matches.
        """
        dataset_to_delete = Dataset.objects.create(title="delete me", deleted="2016-01-01")
        dataset_keep = Dataset.objects.create(title="keep me")

        job = HarvestJobFactory(
            items=[
                HarvestItem(dataset=dataset_to_delete, remote_id="1"),
                HarvestItem(dataset=dataset_keep, remote_id="2"),
                HarvestItem(dataset=dataset_to_delete, remote_id="3"),
            ]
        )

        tasks.purge_datasets()

        job.reload()
        assert job.items[0].dataset is None
        assert job.items[1].dataset == dataset_keep
        assert job.items[2].dataset is None

    def test_purge_datasets_cleans_blocs_in_post_and_site(self):
        dataset_to_delete = Dataset.objects.create(title="delete me", deleted="2016-01-01")
        dataset_keep = Dataset.objects.create(title="keep me")

        bloc = DatasetsListBloc(title="Featured", datasets=[dataset_to_delete, dataset_keep])
        PostFactory(body_type="blocs", blocs=[bloc])
        SiteFactory(id="test-site", datasets_blocs=[bloc])

        tasks.purge_datasets()

        post = Post.objects.first()
        assert len(post.blocs[0].datasets) == 1
        assert post.blocs[0].datasets[0].id == dataset_keep.id

        site = Site.objects.get(id="test-site")
        assert len(site.datasets_blocs[0].datasets) == 1
        assert site.datasets_blocs[0].datasets[0].id == dataset_keep.id

    def test_purge_datasets_community(self):
        dataset = Dataset.objects.create(title="delete me", deleted="2016-01-01")
        community_resource1 = CommunityResourceFactory()
        community_resource1.dataset = dataset
        community_resource1.save()

        tasks.purge_datasets()
        assert CommunityResource.objects.count() == 0

    @pytest.mark.usefixtures("instance_path")
    def test_export_csv(self, app):
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
