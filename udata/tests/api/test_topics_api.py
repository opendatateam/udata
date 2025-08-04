from flask import url_for

from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.factories import SpatialCoverageFactory
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

    def test_topic_api_list(self):
        """It should fetch a topic list from the API"""
        owner = UserFactory()
        org = OrganizationFactory()
        paca, _, _ = create_geozones_fixtures()

        tag_topic_1 = TopicFactory(tags=["my-tag-shared", "my-tag-1"])
        tag_topic_2 = TopicFactory(tags=["my-tag-shared", "my-tag-2"])
        name_topic = TopicFactory(name="topic-for-query")
        private_topic = TopicFactory(private=True)
        geozone_topic = TopicFactory(spatial=SpatialCoverageFactory(zones=[paca.id]))
        granularity_topic = TopicFactory(spatial=SpatialCoverageFactory(granularity="country"))
        featured_topic = TopicFactory(featured=True)
        owner_topic = TopicFactory(owner=owner)
        org_topic = TopicFactory(organization=org)

        response = self.get(url_for("api.topics"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 8)

        response = self.get(url_for("api.topics", q="topic-for"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertEqual(response.json["data"][0]["id"], str(name_topic.id))

        response = self.get(url_for("api.topics", tag=["my-tag-shared", "my-tag-1"]))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertEqual(response.json["data"][0]["id"], str(tag_topic_1.id))
        datasets = response.json["data"][0]["datasets"]
        self.assertEqual(len(datasets), 3)
        for dataset, expected in zip(datasets, [d.fetch() for d in tag_topic_1.datasets]):
            self.assertEqual(dataset["id"], str(expected.id))
            self.assertEqual(dataset["title"], str(expected.title))
            self.assertIsNone(dataset["page"])  # we don't have cdata in tests
            self.assertIsNotNone(dataset["uri"])
        reuses = response.json["data"][0]["reuses"]
        for reuse, expected in zip(reuses, [r.fetch() for r in tag_topic_1.reuses]):
            self.assertEqual(reuse["id"], str(expected.id))
            self.assertEqual(reuse["title"], str(expected.title))
            self.assertIsNone(reuse["page"])  # we don't have cdata in tests
            self.assertIsNotNone(reuse["uri"])
        self.assertEqual(len(reuses), 3)

        response = self.get(url_for("api.topics", tag="my-tag-shared"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 2)
        self.assertEqual(
            set([str(tag_topic_1.id), str(tag_topic_2.id)]),
            set([t["id"] for t in response.json["data"]]),
        )

        response = self.get(url_for("api.topics", include_private="true"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 8)
        # we're not logged in, so the private topic does not appear
        self.assertNotIn(str(private_topic.id), [t["id"] for t in response.json["data"]])

        response = self.get(url_for("api.topics", geozone=paca.id))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertIn(str(geozone_topic.id), [t["id"] for t in response.json["data"]])

        response = self.get(url_for("api.topics", granularity="country"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertIn(str(granularity_topic.id), [t["id"] for t in response.json["data"]])

        response = self.get(url_for("api.topics", featured="true"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertIn(str(featured_topic.id), [t["id"] for t in response.json["data"]])

        response = self.get(url_for("api.topics", featured="false"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 7)
        self.assertNotIn(str(featured_topic.id), [t["id"] for t in response.json["data"]])

        response = self.get(url_for("api.topics", owner=owner.id))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertIn(str(owner_topic.id), [t["id"] for t in response.json["data"]])

        response = self.get(url_for("api.topics", organization=org.id))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertIn(str(org_topic.id), [t["id"] for t in response.json["data"]])

    def test_topic_api_list_authenticated(self):
        owner = self.login()

        private_topic = TopicFactory(private=True)
        private_topic_owner = TopicFactory(private=True, owner=owner)

        response = self.get(url_for("api.topics"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 0)

        response = self.get(url_for("api.topics", include_private="true"))
        self.assert200(response)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertNotIn(str(private_topic.id), [t["id"] for t in response.json["data"]])
        self.assertIn(str(private_topic_owner.id), [t["id"] for t in response.json["data"]])

    def test_topic_api_get(self):
        """It should fetch a topic from the API"""
        topic = TopicFactory()
        response = self.get(url_for("api.topic", topic=topic))
        self.assert200(response)

        data = response.json
        self.assertIn("spatial", data)

        for dataset, expected in zip(data["datasets"], [d.fetch() for d in topic.datasets]):
            self.assertEqual(dataset["id"], str(expected.id))
            self.assertEqual(dataset["title"], str(expected.title))
            self.assertIsNone(dataset["page"])  # we don't have cdata by default
            self.assertIsNotNone(dataset["uri"])

        for reuse, expected in zip(data["reuses"], [r.fetch() for r in topic.reuses]):
            self.assertEqual(reuse["id"], str(expected.id))
            self.assertEqual(reuse["title"], str(expected.title))
            self.assertIsNone(reuse["page"])  # we don't have cdata by default
            self.assertIsNotNone(reuse["uri"])

        self.assertIsNotNone(data.get("created_at"))
        self.assertIsNotNone(data.get("last_modified"))

    def test_topic_api_create(self):
        """It should create a topic from the API"""
        data = TopicFactory.as_dict()
        data["datasets"] = [str(d.id) for d in data["datasets"]]
        data["reuses"] = [str(r.id) for r in data["reuses"]]
        self.login()
        response = self.post(url_for("api.topics"), data)
        self.assert201(response)
        self.assertEqual(Topic.objects.count(), 1)
        topic = Topic.objects.first()
        for dataset, expected in zip(topic.datasets, data["datasets"]):
            self.assertEqual(str(dataset.id), expected)
        for reuse, expected in zip(topic.reuses, data["reuses"]):
            self.assertEqual(str(reuse.id), expected)

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
