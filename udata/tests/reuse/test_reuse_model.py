from datetime import datetime

from udata.models import Reuse

from udata.core.dataset import tasks as dataset_tasks
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory, VisibleReuseFactory
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.user.factories import UserFactory
from udata.core.discussions.factories import DiscussionFactory
from udata.i18n import gettext as _
from udata.tests.helpers import assert_emit

from .. import TestCase, DBTestMixin


class ReuseModelTest(TestCase, DBTestMixin):
    def test_owned_by_user(self):
        user = UserFactory()
        reuse = ReuseFactory(owner=user)
        ReuseFactory(owner=UserFactory())

        result = Reuse.objects.owned_by(user)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], reuse)

    def test_owned_by_org(self):
        org = OrganizationFactory()
        reuse = ReuseFactory(organization=org)
        ReuseFactory(organization=OrganizationFactory())

        result = Reuse.objects.owned_by(org)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], reuse)

    def test_owned_by_org_or_user(self):
        user = UserFactory()
        org = OrganizationFactory()
        reuses = [ReuseFactory(owner=user), ReuseFactory(organization=org)]
        excluded = [ReuseFactory(owner=UserFactory()),
                    ReuseFactory(organization=OrganizationFactory())]

        result = Reuse.objects.owned_by(org, user)

        self.assertEqual(len(result), 2)
        for reuse in result:
            self.assertIn(reuse, reuses)

        for reuse in excluded:
            self.assertNotIn(reuse, result)

    def test_tags_normalized(self):
        user = UserFactory()
        tags = [' one another!', ' one another!', 'This IS a "tag"…']
        reuse = ReuseFactory(owner=user, tags=tags)
        self.assertEqual(len(reuse.tags), 2)
        self.assertEqual(reuse.tags[1], 'this-is-a-tag')

    def test_send_on_delete(self):
        reuse = ReuseFactory()
        with assert_emit(Reuse.on_delete):
            reuse.deleted = datetime.utcnow()
            reuse.save()

    def test_reuse_metrics(self):
        dataset = VisibleDatasetFactory()
        reuse = VisibleReuseFactory()
        DiscussionFactory(subject=reuse)

        reuse.count_datasets()
        reuse.count_discussions()

        assert reuse.get_metrics()['datasets'] == 1
        assert reuse.get_metrics()['discussions'] == 1

        with assert_emit(Reuse.on_update):
            reuse.datasets.append(dataset)
            reuse.save()

        reuse.count_datasets()
        assert reuse.get_metrics()['datasets'] == 2

        dataset.count_reuses()
        assert dataset.get_metrics()['reuses'] == 1

        with assert_emit(Reuse.on_update):
            reuse.datasets.remove(dataset)
            reuse.save()

        dataset_tasks.update_datasets_reuses_metrics()
        dataset.reload()
        assert dataset.get_metrics()['reuses'] == 0

    def test_reuse_type(self):
        reuse = ReuseFactory(type='api')
        self.assertEqual(reuse.type, 'api')
        self.assertEqual(reuse.type_label, 'API')

    def test_reuse_topic(self):
        reuse = ReuseFactory(topic='health')
        self.assertEqual(reuse.topic, 'health')
        self.assertEqual(reuse.topic_label, _('Health'))

    def test_reuse_without_private(self):
        reuse = ReuseFactory()
        self.assertEqual(reuse.private, False)

        reuse.private = None
        reuse.save()
        self.assertEqual(reuse.private, False)

        reuse.private = True
        reuse.save()
        self.assertEqual(reuse.private, True)

