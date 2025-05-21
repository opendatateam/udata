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
        assert all(k in data[0]["elements"] for k in hateoas_fields)

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

        response = self.get(url_for("apiv2.topics_list", include_private="true"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 8
        # we're not logged in, so the private topic does not appear
        assert str(private_topic.id) not in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("apiv2.topics_list", geozone=paca.id))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(geozone_topic.id) in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("apiv2.topics_list", granularity="country"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(granularity_topic.id) in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("apiv2.topics_list", featured="true"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(featured_topic.id) in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("apiv2.topics_list", featured="false"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 7
        assert str(featured_topic.id) not in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("apiv2.topics_list", owner=owner.id))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(owner_topic.id) in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("apiv2.topics_list", organization=org.id))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(org_topic.id) in [t["id"] for t in response.json["data"]]

    def test_topic_api_list_authenticated(self):
        owner = self.login()

        private_topic = TopicFactory(private=True)
        private_topic_owner = TopicFactory(private=True, owner=owner)

        response = self.get(url_for("apiv2.topics_list"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 0

        response = self.get(url_for("apiv2.topics_list", include_private="true"))
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

        response = self.get(topic_response.json["elements"]["href"])
        data = response.json
        assert all(str(elt.id) in (_elt["id"] for _elt in data["data"]) for elt in topic.elements)


class TopicElementsAPITest(APITestCase):
    def test_elements_list(self):
        topic = TopicFactory()
        response = self.get(url_for("apiv2.topic_elements", topic=topic))
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 3
        assert all(str(elt.id) in (_elt["id"] for _elt in data) for elt in topic.elements)

    def test_add_elements(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        dataset = DatasetFactory()
        reuse = ReuseFactory()
        response = self.post(
            url_for("apiv2.topic_elements", topic=topic),
            [
                {
                    "title": "A dataset",
                    "description": "A dataset description",
                    "tags": ["tag1", "tag2"],
                    "extras": {"extra": "value"},
                    "element": {"class": "Dataset", "id": dataset.id},
                },
                {
                    "title": "A reuse",
                    "description": "A reuse description",
                    "tags": ["tag1", "tag2"],
                    "extras": {"extra": "value"},
                    "element": {"class": "Reuse", "id": reuse.id},
                },
            ],
        )
        assert response.status_code == 201
        topic.reload()
        assert len(topic.elements) == 5

        dataset_elt = next(elt for elt in topic.elements if elt.element.id == dataset.id)
        assert dataset_elt.title == "A dataset"
        assert dataset_elt.description == "A dataset description"
        assert dataset_elt.tags == ["tag1", "tag2"]
        assert dataset_elt.extras == {"extra": "value"}

        reuse_elt = next(elt for elt in topic.elements if elt.element.id == reuse.id)
        assert reuse_elt.title == "A reuse"
        assert reuse_elt.description == "A reuse description"
        assert reuse_elt.tags == ["tag1", "tag2"]
        assert reuse_elt.extras == {"extra": "value"}

    def test_add_element_wrong_class(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        dataset = DatasetFactory()
        response = self.post(
            url_for("apiv2.topic_elements", topic=topic),
            [{"element": {"class": "Reuse", "id": dataset.id}}],
        )
        assert response.status_code == 400
        assert "n'existe pas" in response.json["errors"][0]["element"][0]

    def test_add_empty_element(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        response = self.post(url_for("apiv2.topic_elements", topic=topic), [{}])
        assert response.status_code == 400
        assert (
            response.json["errors"][0]["element"][0]
            == "A topic element must have a title or an element."
        )

    def test_add_datasets_perm(self):
        user = UserFactory()
        topic = TopicFactory(owner=user)
        dataset = DatasetFactory()
        self.login()
        response = self.post(url_for("apiv2.topic_elements", topic=topic), [{"id": dataset.id}])
        assert response.status_code == 403

    def test_add_datasets_wrong_payload(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        response = self.post(url_for("apiv2.topic_elements", topic=topic), [{"id": "xxx"}])
        assert response.status_code == 400
        response = self.post(url_for("apiv2.topic_elements", topic=topic), [{"nain": "portekoi"}])
        assert response.status_code == 400
        response = self.post(url_for("apiv2.topic_elements", topic=topic), {"non": "mais"})
        assert response.status_code == 400


class TopicElementAPITest(APITestCase):
    def test_delete_element(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        element = topic.elements[0]
        response = self.delete(url_for("apiv2.topic_element", topic=topic, element_id=element.id))
        assert response.status_code == 204
        topic.reload()
        assert len(topic.elements) == 2
        assert element.id not in (elt.id for elt in topic.elements)

    def test_delete_element_perm(self):
        topic = TopicFactory(owner=UserFactory())
        element = topic.elements[0]
        self.login()
        response = self.delete(url_for("apiv2.topic_element", topic=topic, element_id=element.id))
        assert response.status_code == 403
