from flask import url_for

from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.models import spatial_granularities
from udata.core.topic.factories import TopicFactory
from udata.core.topic.models import Topic
from udata.core.user.factories import UserFactory
from udata.models import Discussion, Member
from udata.tests.api.test_datasets_api import SAMPLE_GEOM
from udata.tests.features.territories import create_geozones_fixtures

from . import APITestCase


class TopicsAPITest(APITestCase):
    modules = []

    # FIXME: migrate to v2
    def test_topic_api_create_as_org(self):
        """It should create a topic as organization from the API"""
        data = TopicFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        user = self.login()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        data["organization"] = str(org.id)
        response = self.post(url_for("api.topics"), data)
        self.assert201(response)
        self.assertEqual(Topic.objects.count(), 1)

        topic = Topic.objects.first()
        assert topic.owner is None
        assert topic.organization == org

    def test_topic_api_create_spatial_zone(self):
        paca, _, _ = create_geozones_fixtures()
        granularity = spatial_granularities[0][0]
        data = TopicFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        data["spatial"] = {
            "zones": [paca.id],
            "granularity": granularity,
        }
        self.login()
        response = self.post(url_for("api.topics"), data)
        self.assert201(response)
        self.assertEqual(Topic.objects.count(), 1)
        topic = Topic.objects.first()
        self.assertEqual([str(z) for z in topic.spatial.zones], [paca.id])
        self.assertEqual(topic.spatial.granularity, granularity)

    def test_topic_api_create_spatial_geom(self):
        granularity = spatial_granularities[0][0]
        data = TopicFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        data["spatial"] = {
            "geom": SAMPLE_GEOM,
            "granularity": granularity,
        }
        self.login()
        response = self.post(url_for("api.topics"), data)
        self.assert201(response)
        self.assertEqual(Topic.objects.count(), 1)
        topic = Topic.objects.first()
        self.assertEqual(topic.spatial.geom, SAMPLE_GEOM)
        self.assertEqual(topic.spatial.granularity, granularity)

    def test_topic_api_update(self):
        """It should update a topic from the API"""
        owner = self.login()
        topic = TopicFactory(owner=owner)
        data = topic.to_dict()
        data["description"] = "new description"
        response = self.put(url_for("api.topic", topic=topic), data)
        self.assert200(response)
        self.assertEqual(Topic.objects.count(), 1)
        topic = Topic.objects.first()
        self.assertEqual(topic.description, "new description")
        self.assertGreater(topic.last_modified, topic.created_at)

    def test_topic_api_update_perm(self):
        """It should not update a topic from the API"""
        owner = UserFactory()
        topic = TopicFactory(owner=owner)
        user = self.login()
        data = topic.to_dict()
        data["owner"] = user.to_dict()
        response = self.put(url_for("api.topic", topic=topic), data)
        self.assert403(response)

    def test_topic_api_clear_datasets(self):
        """It should remove all datasets if set to None"""
        owner = self.login()
        topic = TopicFactory(owner=owner)
        self.assertGreater(len(topic.datasets), 0)
        data = topic.to_dict()
        data["datasets"] = None
        response = self.put(url_for("api.topic", topic=topic), data)
        self.assert200(response)
        topic.reload()
        self.assertEqual(len(topic.datasets), 0)

    def test_topic_api_delete(self):
        """It should delete a topic from the API"""
        owner = self.login()
        topic = TopicFactory(owner=owner)

        with self.api_user():
            response = self.post(
                url_for("api.discussions"),
                {
                    "title": "test title",
                    "comment": "bla bla",
                    "subject": {
                        "class": "Topic",
                        "id": topic.id,
                    },
                },
            )
        self.assert201(response)

        discussions = Discussion.objects(subject=topic)
        self.assertEqual(len(discussions), 1)

        with self.api_user():
            response = self.delete(url_for("api.topic", topic=topic))
        self.assertStatus(response, 204)

        self.assertEqual(Topic.objects.count(), 0)
        self.assertEqual(Discussion.objects.count(), 0)

    def test_topic_api_delete_perm(self):
        """It should not delete a topic from the API"""
        owner = UserFactory()
        topic = TopicFactory(owner=owner)
        with self.api_user():
            response = self.delete(url_for("api.topic", topic=topic))
        self.assertStatus(response, 403)
