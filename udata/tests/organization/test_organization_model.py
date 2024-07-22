from datetime import datetime

from udata.core.dataset.factories import DatasetFactory, HiddenDatasetFactory
from udata.core.followers.signals import on_follow, on_unfollow
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory, VisibleReuseFactory
from udata.core.user.factories import UserFactory
from udata.models import Dataset, Follow, Member, Reuse
from udata.tests.helpers import assert_emit

from .. import DBTestMixin, TestCase


class OrganizationModelTest(TestCase, DBTestMixin):
    # Load metrics
    import udata.core.organization.metrics  # noqa
    import udata.core.followers.metrics  # noqa

    def test_organization_metrics(self):
        # Members count update are in API calls, thus being tested in API dedicated tests

        member = Member(user=UserFactory(), role="admin")
        org = OrganizationFactory(members=[member])

        with assert_emit(Reuse.on_create):
            reuse = VisibleReuseFactory(organization=org)
            ReuseFactory(organization=org)
        with assert_emit(Dataset.on_create):
            dataset = DatasetFactory(organization=org)
            HiddenDatasetFactory(organization=org)
        with assert_emit(on_follow):
            follow = Follow.objects.create(
                following=org, follower=UserFactory(), since=datetime.utcnow()
            )

        assert org.get_metrics()["datasets"] == 1
        assert org.get_metrics()["reuses"] == 1
        assert org.get_metrics()["followers"] == 1

        with assert_emit(Reuse.on_delete):
            reuse.deleted = datetime.utcnow()
            reuse.save()
        with assert_emit(Dataset.on_delete):
            dataset.deleted = datetime.utcnow()
            dataset.save()
        with assert_emit(on_unfollow):
            follow.until = datetime.utcnow()
            follow.save()

        assert org.get_metrics()["datasets"] == 0
        assert org.get_metrics()["reuses"] == 0
        assert org.get_metrics()["followers"] == 0
