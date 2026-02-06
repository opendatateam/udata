from udata.core.activity.models import Activity
from udata.core.dataservices import tasks
from udata.core.dataservices.models import Dataservice
from udata.core.user.factories import UserFactory
from udata.harvest.models import HarvestItem, HarvestJob
from udata.harvest.tests.factories import HarvestJobFactory
from udata.models import Discussion, Follow, Message, Transfer
from udata.tests.api import PytestOnlyDBTestCase
from udata.utils import faker


class DataserviceTasksTest(PytestOnlyDBTestCase):
    def test_purge_dataservices(self):
        dataservices = [
            Dataservice.objects.create(
                title="delete me", base_api_url="https://example.com/api", deleted_at="2016-01-01"
            ),
            Dataservice.objects.create(title="keep me", base_api_url="https://example.com/api"),
        ]

        user = UserFactory()
        transfer = Transfer.objects.create(
            owner=user,
            recipient=user,
            subject=dataservices[0],
            comment="comment",
        )

        discussion = Discussion.objects.create(
            subject=dataservices[0],
            user=user,
            title="test discussion",
            discussion=[Message(content=faker.sentence(), posted_by=user)],
        )

        follower = Follow.objects.create(follower=user, following=dataservices[0])

        activity = Activity.objects.create(actor=UserFactory(), related_to=dataservices[0].id)

        HarvestJobFactory(items=[HarvestItem(dataservice=dataservices[0])])

        tasks.purge_dataservices()

        assert Dataservice.objects.count() == 1
        assert Transfer.objects.filter(id=transfer.id).count() == 0
        assert Discussion.objects.filter(id=discussion.id).count() == 0
        assert Follow.objects.filter(id=follower.id).count() == 0
        assert HarvestJob.objects.filter(items__dataservice=dataservices[0].id).count() == 0
        assert Activity.objects.filter(id=activity.id).count() == 0

    def test_purge_dataservices_cleans_all_harvest_items_references(self):
        """Test that purging dataservices cleans all HarvestItem references in a job.

        The same dataservice can appear multiple times in a job's items (e.g. if the
        harvest source has duplicates). The $ operator only updates the first match,
        so we need to use $[] with array_filters to update all matches.
        """
        dataservice_to_delete = Dataservice.objects.create(
            title="delete me", base_api_url="https://example.com/api", deleted_at="2016-01-01"
        )
        dataservice_keep = Dataservice.objects.create(
            title="keep me", base_api_url="https://example.com/api"
        )

        job = HarvestJobFactory(
            items=[
                HarvestItem(dataservice=dataservice_to_delete, remote_id="1"),
                HarvestItem(dataservice=dataservice_keep, remote_id="2"),
                HarvestItem(dataservice=dataservice_to_delete, remote_id="3"),
            ]
        )

        tasks.purge_dataservices()

        job.reload()
        assert job.items[0].dataservice is None
        assert job.items[1].dataservice == dataservice_keep
        assert job.items[2].dataservice is None
