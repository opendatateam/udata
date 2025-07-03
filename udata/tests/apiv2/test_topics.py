from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.spatial.factories import SpatialCoverageFactory
from udata.core.topic.factories import TopicFactory
from udata.core.user.factories import UserFactory
from udata.tests.api import APITestCase
from udata.tests.features.territories import create_geozones_fixtures


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

        response = self.get(url_for("apiv2.topics_list"))
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 8

        hateoas_fields = ["rel", "href", "type", "total"]
        assert all(k in data[0]["datasets"] for k in hateoas_fields)
        assert all(k in data[0]["reuses"] for k in hateoas_fields)

        response = self.get(url_for("apiv2.topics_list", q="topic-for"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(name_topic.id)

        response = self.get(url_for("apiv2.topics_list", tag=["my-tag-shared", "my-tag-1"]))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(tag_topic_1.id)

        response = self.get(url_for("apiv2.topics_list", tag=["my-tag-shared"]))
        assert response.status_code == 200
        assert len(response.json["data"]) == 2
        self.assertEqual(
            set([str(tag_topic_1.id), str(tag_topic_2.id)]),
            set([t["id"] for t in response.json["data"]]),
        )

        response = self.get(url_for("api.topics", include_private="true"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 8
        # we're not logged in, so the private topic does not appear
        assert str(private_topic.id) not in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("api.topics", geozone=paca.id))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(geozone_topic.id) in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("api.topics", granularity="country"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(granularity_topic.id) in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("api.topics", featured="true"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(featured_topic.id) in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("api.topics", featured="false"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 7
        assert str(featured_topic.id) not in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("api.topics", owner=owner.id))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(owner_topic.id) in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("api.topics", organization=org.id))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(org_topic.id) in [t["id"] for t in response.json["data"]]

    def test_topic_api_list_authenticated(self):
        owner = self.login()

        private_topic = TopicFactory(private=True)
        private_topic_owner = TopicFactory(private=True, owner=owner)

        response = self.get(url_for("api.topics"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 0

        response = self.get(url_for("api.topics", include_private="true"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(private_topic.id) not in [t["id"] for t in response.json["data"]]
        assert str(private_topic_owner.id) in [t["id"] for t in response.json["data"]]

    def test_topic_api_get(self):
        """It should fetch a topic from the API"""
        topic = TopicFactory()
        topic_response = self.get(url_for("apiv2.topic", topic=topic))
        assert topic_response.status_code == 200
        assert "spatial" in topic_response.json

        assert topic_response.json["created_at"] is not None
        assert topic_response.json["last_modified"] is not None

        response = self.get(topic_response.json["datasets"]["href"])
        data = response.json
        assert all(str(d.id) in (_d["id"] for _d in data["data"]) for d in topic.datasets)

        response = self.get(topic_response.json["reuses"]["href"])
        data = response.json
        assert all(str(r.id) in (_r["id"] for _r in data["data"]) for r in topic.reuses)


class TopicDatasetsAPITest(APITestCase):
    def test_list(self):
        topic = TopicFactory()
        response = self.get(url_for("apiv2.topic_datasets", topic=topic))
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 3
        assert all(str(d.id) in (_d["id"] for _d in data) for d in topic.datasets)

    def test_add_datasets(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        d1, d2 = DatasetFactory.create_batch(2)
        response = self.post(
            url_for("apiv2.topic_datasets", topic=topic), [{"id": d1.id}, {"id": d2.id}]
        )
        assert response.status_code == 201
        topic.reload()
        assert len(topic.datasets) == 5
        assert all(d.id in (_d.id for _d in topic.datasets) for d in (d1, d2))

    def test_add_datasets_double(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        dataset = DatasetFactory()
        response = self.post(
            url_for("apiv2.topic_datasets", topic=topic), [{"id": dataset.id}, {"id": dataset.id}]
        )
        assert response.status_code == 201
        topic.reload()
        assert len(topic.datasets) == 4
        response = self.post(url_for("apiv2.topic_datasets", topic=topic), [{"id": dataset.id}])
        assert response.status_code == 201
        topic.reload()
        assert len(topic.datasets) == 4

    def test_add_datasets_perm(self):
        user = UserFactory()
        topic = TopicFactory(owner=user)
        dataset = DatasetFactory()
        self.login()
        response = self.post(url_for("apiv2.topic_datasets", topic=topic), [{"id": dataset.id}])
        assert response.status_code == 403

    def test_add_datasets_wrong_payload(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        response = self.post(url_for("apiv2.topic_datasets", topic=topic), [{"id": "xxx"}])
        assert response.status_code == 400
        response = self.post(url_for("apiv2.topic_datasets", topic=topic), [{"nain": "portekoi"}])
        assert response.status_code == 400
        response = self.post(url_for("apiv2.topic_datasets", topic=topic), {"non": "mais"})
        assert response.status_code == 400


class TopicDatasetAPITest(APITestCase):
    def test_delete_dataset(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        dataset = topic.datasets[0]
        response = self.delete(url_for("apiv2.topic_dataset", topic=topic, dataset=dataset))
        assert response.status_code == 204
        topic.reload()
        assert len(topic.datasets) == 2
        assert dataset.id not in (d.id for d in topic.datasets)

    def test_delete_dataset_perm(self):
        topic = TopicFactory(owner=UserFactory())
        dataset = topic.datasets[0]
        self.login()
        response = self.delete(url_for("apiv2.topic_dataset", topic=topic, dataset=dataset))
        assert response.status_code == 403


class TopicReusesAPITest(APITestCase):
    def test_list(self):
        topic = TopicFactory()
        response = self.get(url_for("apiv2.topic_reuses", topic=topic))
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 3
        assert all(str(r.id) in (_r["id"] for _r in data) for r in topic.reuses)

    def test_add_reuses(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        r1, r2 = ReuseFactory.create_batch(2)
        response = self.post(
            url_for("apiv2.topic_reuses", topic=topic), [{"id": r1.id}, {"id": r2.id}]
        )
        assert response.status_code == 201
        topic.reload()
        assert len(topic.reuses) == 5
        assert all(r.id in (_r.id for _r in topic.reuses) for r in (r1, r2))

    def test_add_reuses_double(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        reuse = ReuseFactory()
        response = self.post(
            url_for("apiv2.topic_reuses", topic=topic), [{"id": reuse.id}, {"id": reuse.id}]
        )
        assert response.status_code == 201
        topic.reload()
        assert len(topic.reuses) == 4
        response = self.post(url_for("apiv2.topic_reuses", topic=topic), [{"id": reuse.id}])
        assert response.status_code == 201
        topic.reload()
        assert len(topic.reuses) == 4

    def test_add_reuses_perm(self):
        user = UserFactory()
        topic = TopicFactory(owner=user)
        reuse = ReuseFactory()
        self.login()
        response = self.post(url_for("apiv2.topic_reuses", topic=topic), [{"id": reuse.id}])
        assert response.status_code == 403

    def test_add_reuses_wrong_payload(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        response = self.post(url_for("apiv2.topic_reuses", topic=topic), [{"id": "xxx"}])
        assert response.status_code == 400
        response = self.post(url_for("apiv2.topic_reuses", topic=topic), [{"nain": "portekoi"}])
        assert response.status_code == 400
        response = self.post(url_for("apiv2.topic_reuses", topic=topic), {"non": "mais"})
        assert response.status_code == 400


class TopicReuseAPITest(APITestCase):
    def test_delete_reuse(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        reuse = topic.reuses[0]
        response = self.delete(url_for("apiv2.topic_reuse", topic=topic, reuse=reuse))
        assert response.status_code == 204
        topic.reload()
        assert len(topic.reuses) == 2
        assert reuse.id not in (d.id for d in topic.reuses)

    def test_delete_reuse_perm(self):
        topic = TopicFactory(owner=UserFactory())
        reuse = topic.reuses[0]
        self.login()
        response = self.delete(url_for("apiv2.topic_reuse", topic=topic, reuse=reuse))
        assert response.status_code == 403
