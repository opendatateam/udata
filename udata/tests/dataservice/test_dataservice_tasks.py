import pytest

from udata.core.dataservices import tasks
from udata.core.dataservices.models import Dataservice
from udata.core.user.factories import UserFactory
from udata.harvest.models import HarvestItem, HarvestJob
from udata.harvest.tests.factories import HarvestJobFactory
from udata.models import Discussion, Follow, Message, Transfer
from udata.utils import faker

pytestmark = pytest.mark.usefixtures("clean_db")


def test_purge_dataservices():
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

    HarvestJobFactory(items=[HarvestItem(dataservice=dataservices[0])])

    tasks.purge_dataservices()

    assert Dataservice.objects.count() == 1
    assert Transfer.objects.filter(id=transfer.id).count() == 0
    assert Discussion.objects.filter(id=discussion.id).count() == 0
    assert Follow.objects.filter(id=follower.id).count() == 0
    assert HarvestJob.objects.filter(items__dataservice=dataservices[0].id).count() == 0
