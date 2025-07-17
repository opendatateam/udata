from flask import url_for

from udata.core import storages
from udata.core.reuse import tasks
from udata.core.reuse.factories import ReuseFactory
from udata.core.topic.models import Topic, TopicElement
from udata.core.user.factories import AdminFactory, UserFactory
from udata.models import Reuse, Transfer
from udata.tests.api import APITestCase
from udata.tests.helpers import create_test_image


class ReuseTasksTest(APITestCase):
    def test_purge_reuses(self):
        reuse = ReuseFactory(title="test-reuse")

        # Upload reuse's image
        file = create_test_image()
        user = AdminFactory()
        self.login(user)
        response = self.post(
            url_for("api.reuse_image", reuse=reuse), {"file": (file, "test.png")}, json=False
        )
        self.assert200(response)

        topic = Topic.objects.create(name="test topic")
        topic_element = TopicElement(element=reuse, topic=topic)
        topic_element.save()

        # Delete reuse
        response = self.delete(url_for("api.reuse", reuse=reuse))
        self.assert204(response)

        user = UserFactory()
        transfer = Transfer.objects.create(
            owner=user,
            recipient=user,
            subject=reuse,
            comment="comment",
        )

        tasks.purge_reuses()

        assert Transfer.objects.filter(id=transfer.id).count() == 0

        topic = Topic.objects(name="test topic").first()
        element = topic.elements.first()
        assert element.element is None

        # Check reuse's image is deleted
        self.assertEqual(list(storages.images.list_files()), [])

        deleted_reuse = Reuse.objects(title="test-reuse").first()
        self.assertIsNone(deleted_reuse)
