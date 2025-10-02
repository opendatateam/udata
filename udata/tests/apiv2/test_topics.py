import pytest
from flask import url_for

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.discussions.models import Discussion
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.reuse.factories import ReuseFactory
from udata.core.spatial.factories import SpatialCoverageFactory
from udata.core.spatial.models import spatial_granularities
from udata.core.topic import DEFAULT_PAGE_SIZE
from udata.core.topic.activities import UserCreatedTopicElement, UserUpdatedTopicElement
from udata.core.topic.factories import (
    TopicElementDatasetFactory,
    TopicElementFactory,
    TopicElementReuseFactory,
    TopicFactory,
    TopicWithElementsFactory,
)
from udata.core.topic.models import Topic, TopicElement
from udata.core.user.factories import UserFactory
from udata.tests.api import APITestCase
from udata.tests.api.test_datasets_api import SAMPLE_GEOM
from udata.tests.features.territories import create_geozones_fixtures


class TopicsListAPITest(APITestCase):
    modules = []

    def test_topic_api_list(self):
        """It should fetch a topic list from the API"""
        owner = UserFactory()
        org = OrganizationFactory()
        paca, _, _ = create_geozones_fixtures()

        tag_topic_1 = TopicFactory(tags=["my-tag-shared", "my-tag-1"])
        tag_topic_2 = TopicFactory(tags=["my-tag-shared", "my-tag-2"])
        private_topic = TopicFactory(private=True)
        geozone_topic = TopicFactory(spatial=SpatialCoverageFactory(zones=[paca.id]))
        granularity_topic = TopicFactory(spatial=SpatialCoverageFactory(granularity="country"))
        featured_topic = TopicFactory(featured=True)
        owner_topic = TopicFactory(owner=owner)
        org_topic = TopicFactory(organization=org)

        response = self.get(url_for("apiv2.topics_list"))
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 7

        hateoas_fields = ["rel", "href", "type", "total"]
        assert all(k in data[0]["elements"] for k in hateoas_fields)

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
        assert len(response.json["data"]) == 7
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
        assert len(response.json["data"]) == 6
        assert str(featured_topic.id) not in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("apiv2.topics_list", owner=owner.id))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(owner_topic.id) in [t["id"] for t in response.json["data"]]

        response = self.get(url_for("apiv2.topics_list", organization=org.id))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert str(org_topic.id) in [t["id"] for t in response.json["data"]]

    def test_topic_api_list_search(self):
        topic = TopicFactory(name="topic-for-test")
        response = self.get(url_for("apiv2.topics_list", q="topic-for"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(topic.id)

        topic = TopicFactory(name="aménagement")
        response = self.get(url_for("apiv2.topics_list", q="amenagement"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(topic.id)

        # this is because we have an "AND" clause in TopicApiParser for q
        topic = TopicFactory(name="aménagement sols")
        response = self.get(url_for("apiv2.topics_list", q="amenagement urbain"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 0

    def test_topic_api_list_search_description(self):
        topic = TopicFactory(name="xxx", description="aménagement")
        response = self.get(url_for("apiv2.topics_list", q="amenagement"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(topic.id)

    def test_topic_api_list_search_by_element_content(self):
        """It should find topics by searching their elements' content"""
        topic_with_matching_element = TopicFactory(
            name="unrelated topic", description="unrelated description"
        )
        TopicElementFactory(
            topic=topic_with_matching_element,
            title="climate change data",
            description="environmental datasets about climate",
        )

        topic_without_matching_element = TopicFactory(
            name="other topic", description="other description"
        )
        TopicElementFactory(
            topic=topic_without_matching_element,
            title="unrelated element",
            description="unrelated element description",
        )

        response = self.get(url_for("apiv2.topics_list", q="climate"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(topic_with_matching_element.id)

        response = self.get(url_for("apiv2.topics_list", q="environmental"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(topic_with_matching_element.id)

        response = self.get(url_for("apiv2.topics_list", q="nonexistent"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 0

    def test_topic_api_list_search_combined_topic_and_element(self):
        """It should find topics that match either in topic content OR element content"""
        topic_matches_itself = TopicFactory(
            name="climate policy", description="environmental policy"
        )

        topic_matches_through_element = TopicFactory(
            name="data collection", description="research data"
        )
        TopicElementFactory(
            topic=topic_matches_through_element,
            title="climate research",
            description="climate change studies",
        )

        response = self.get(url_for("apiv2.topics_list", q="climate"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 2

        topic_ids = {t["id"] for t in response.json["data"]}
        assert str(topic_matches_itself.id) in topic_ids
        assert str(topic_matches_through_element.id) in topic_ids

    def test_topic_api_list_search_by_element_content_diacritics(self):
        """It should find topics by searching their elements' content with diacritics support"""
        topic_with_accents = TopicFactory(name="data topic", description="data collection")
        TopicElementFactory(
            topic=topic_with_accents, title="Système de données", description="Création d'un modèle"
        )

        topic_without_accents = TopicFactory(name="other topic", description="other description")
        TopicElementFactory(
            topic=topic_without_accents,
            title="systeme de donnees",
            description="creation d'un modele",
        )

        response = self.get(url_for("apiv2.topics_list", q="systeme donnees"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 2
        topic_ids = {t["id"] for t in response.json["data"]}
        assert str(topic_with_accents.id) in topic_ids
        assert str(topic_without_accents.id) in topic_ids

        response = self.get(url_for("apiv2.topics_list", q="création modèle"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 2
        topic_ids = {t["id"] for t in response.json["data"]}
        assert str(topic_with_accents.id) in topic_ids
        assert str(topic_without_accents.id) in topic_ids

    # TODO: this would work with the following index on Topic,
    # but we need to find a way to inject the language from config:
    #   meta = {
    #     "indexes": [
    #       {"fields": ["$name", "$description"], 'default_language': 'fr'}
    #     ]
    #   }
    @pytest.mark.skip()
    def test_topic_api_list_search_advanced(self):
        topic = TopicFactory(name="plans d'eau")
        response = self.get(url_for("apiv2.topics_list", q="eau"))
        assert response.status_code == 200
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(topic.id)

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
        topic = TopicWithElementsFactory()
        topic_response = self.get(url_for("apiv2.topic", topic=topic))
        assert topic_response.status_code == 200
        assert "spatial" in topic_response.json

        assert topic_response.json["created_at"] is not None
        assert topic_response.json["last_modified"] is not None

        response = self.get(topic_response.json["elements"]["href"])
        data = response.json
        assert all(
            str(elt.id) in (_elt["id"] for _elt in data["data"])
            for elt in TopicElement.objects(topic=topic)
        )

    def test_topic_api_create(self):
        """It should create a topic from the API"""
        data = TopicWithElementsFactory.as_payload()
        self.login()
        response = self.post(url_for("apiv2.topics_list"), data)
        self.assert201(response)
        self.assertEqual(Topic.objects.count(), 1)
        topic = Topic.objects.first()
        for element in data["elements"]:
            assert element["element"]["id"] in (
                str(elt.element.id) for elt in TopicElement.objects(topic=topic)
            )

    def test_topic_api_create_element_no_inherit_parent_fields(self):
        """It should create topic elements without inheriting parent topic's description/tags"""
        dataset = DatasetFactory()
        data = {
            "name": "Test Topic with Element",
            "description": "Topic description that should NOT be inherited",
            "tags": ["topic-tag-1", "topic-tag-2"],
            "elements": [{"element": {"class": "Dataset", "id": str(dataset.id)}}],
        }
        self.login()
        response = self.post(url_for("apiv2.topics_list"), data)
        self.assert201(response)

        topic = Topic.objects.first()
        element = TopicElement.objects(topic=topic).first()

        # Element should NOT inherit parent topic's fields when not provided
        assert element.description is None
        assert element.tags == []

        # But parent topic should have its fields
        assert topic.description == "Topic description that should NOT be inherited"
        assert topic.tags == ["topic-tag-1", "topic-tag-2"]

    def test_topic_api_create_as_org(self):
        """It should create a topic as organization from the API"""
        data = TopicWithElementsFactory.as_payload()
        user = self.login()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        data["organization"] = str(org.id)
        response = self.post(url_for("apiv2.topics_list"), data)
        self.assert201(response)
        self.assertEqual(Topic.objects.count(), 1)

        topic = Topic.objects.first()
        assert topic.owner is None
        assert topic.organization == org

    def test_topic_api_create_spatial_zone(self):
        paca, _, _ = create_geozones_fixtures()
        granularity = spatial_granularities[0][0]
        data = TopicWithElementsFactory.as_payload()
        data["spatial"] = {
            "zones": [paca.id],
            "granularity": granularity,
        }
        self.login()
        response = self.post(url_for("apiv2.topics_list"), data)
        self.assert201(response)
        self.assertEqual(Topic.objects.count(), 1)
        topic = Topic.objects.first()
        self.assertEqual([str(z) for z in topic.spatial.zones], [paca.id])
        self.assertEqual(topic.spatial.granularity, granularity)

    def test_topic_api_create_spatial_geom(self):
        granularity = spatial_granularities[0][0]
        data = TopicWithElementsFactory.as_payload()
        data["spatial"] = {
            "geom": SAMPLE_GEOM,
            "granularity": granularity,
        }
        self.login()
        response = self.post(url_for("apiv2.topics_list"), data)
        self.assert201(response)
        self.assertEqual(Topic.objects.count(), 1)
        topic = Topic.objects.first()
        self.assertEqual(topic.spatial.geom, SAMPLE_GEOM)
        self.assertEqual(topic.spatial.granularity, granularity)


class TopicAPITest(APITestCase):
    def test_topic_api_update(self):
        """It should update a topic from the API"""
        owner = self.login()
        topic = TopicFactory(owner=owner)
        data = topic.to_dict()
        data["description"] = "new description"
        response = self.put(url_for("apiv2.topic", topic=topic), data)
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
        response = self.put(url_for("apiv2.topic", topic=topic), data)
        self.assert403(response)

    def test_topic_api_update_with_elements(self):
        """It should update a topic from the API with elements parameters"""
        user = self.login()
        topic = TopicWithElementsFactory(owner=user)
        initial_length = len(topic.elements)
        data = topic.to_dict()
        data["elements"] = [TopicElementFactory.element_as_payload(elt) for elt in topic.elements]
        data["elements"].append(
            TopicElementFactory.element_as_payload(TopicElementDatasetFactory())
        )
        response = self.put(url_for("apiv2.topic", topic=topic), data)
        self.assert200(response)
        topic.reload()
        self.assertEqual(len(topic.elements), initial_length + 1)

    def test_topic_api_update_without_elements(self):
        """It should update a topic without affecting existing elements when elements field is not provided"""
        user = self.login()
        topic = TopicWithElementsFactory(owner=user)
        initial_element_ids = [str(elt.id) for elt in topic.elements]

        # Update topic without including elements field
        data = {
            "name": "Updated topic name",
            "description": "Updated description",
            "tags": ["updated-tag"],
        }
        response = self.put(url_for("apiv2.topic", topic=topic), data)
        self.assert200(response)

        # Reload and verify elements are preserved
        topic.reload()
        self.assertEqual(len(topic.elements), len(initial_element_ids))
        current_element_ids = [str(elt.id) for elt in topic.elements]
        self.assertEqual(set(current_element_ids), set(initial_element_ids))

        # Verify other fields were updated
        self.assertEqual(topic.name, "Updated topic name")
        self.assertEqual(topic.description, "Updated description")
        self.assertEqual(topic.tags, ["updated-tag"])

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
            response = self.delete(url_for("apiv2.topic", topic=topic))
        self.assertStatus(response, 204)

        self.assertEqual(Topic.objects.count(), 0)
        self.assertEqual(Discussion.objects.count(), 0)

    def test_topic_api_delete_perm(self):
        """It should not delete a topic from the API"""
        owner = UserFactory()
        topic = TopicFactory(owner=owner)
        with self.api_user():
            response = self.delete(url_for("apiv2.topic", topic=topic))
        self.assertStatus(response, 403)

    def test_topic_api_uri_is_absolute(self):
        """It should return an absolute URI for topic API"""
        topic = TopicFactory()
        response = self.get(url_for("apiv2.topic", topic=topic))
        self.assert200(response)
        data = response.json

        self.assertIn("uri", data)
        self.assertTrue(data["uri"].startswith("http"))


class TopicElementsAPITest(APITestCase):
    def test_elements_list(self):
        topic = TopicFactory()
        reuse_elt = TopicElementReuseFactory(
            topic=topic, tags=["foo", "bar"], extras={"foo": "bar"}
        )
        dataset_elt = TopicElementDatasetFactory(
            topic=topic, tags=["foo", "bar"], extras={"foo": "bar"}
        )
        TopicElementFactory(topic=topic, tags=["foo", "bar"], extras={"foo": "bar"})
        response = self.get(url_for("apiv2.topic_elements", topic=topic))
        assert response.status_code == 200
        data = response.json["data"]
        assert len(data) == 3
        assert all(_elt["tags"] == ["foo", "bar"] for _elt in data)
        assert all(_elt["extras"] == {"foo": "bar"} for _elt in data)
        assert {"class": "Reuse", "id": str(reuse_elt.element.id)} in [
            _elt["element"] for _elt in data
        ]
        assert {"class": "Dataset", "id": str(dataset_elt.element.id)} in [
            _elt["element"] for _elt in data
        ]
        no_elt = next(_elt for _elt in data if not _elt["element"])
        assert no_elt["element"] is None

    def test_elements_list_pagination(self):
        topic = TopicFactory()
        for _ in range(DEFAULT_PAGE_SIZE + 1):
            TopicElementFactory(topic=topic)
        response = self.get(url_for("apiv2.topic_elements", topic=topic))
        assert response.status_code == 200
        assert response.json["next_page"] is not None
        first_page_ids = [elt["id"] for elt in response.json["data"]]
        response = self.get(response.json["next_page"])
        assert response.status_code == 200
        assert response.json["next_page"] is None
        assert response.json["data"][0]["id"] not in first_page_ids

    def test_elements_list_search(self):
        topic = TopicFactory()
        matches_1 = [
            TopicElementFactory(topic=topic, title="Apprentissage automatique et algorithmes"),
            TopicElementFactory(
                topic=topic,
                description="Ceci concerne l'apprentissage automatique et les algorithmes d'intelligence artificielle",
            ),
            TopicElementFactory(topic=topic, title="algorithmes d'apprentissage"),
        ]
        # Diacritics test
        TopicElementFactory(topic=topic, title="Système de données")
        TopicElementFactory(topic=topic, description="Création d'un modèle")

        # Create non-matching elements
        TopicElementFactory(topic=topic, title="ne devrait pas apparaître")
        TopicElementFactory(topic=topic, description="contenu non pertinent")
        TopicElementFactory(topic=topic, title="appr algo")  # Partial words that regex might catch

        # Test with French phrase
        response = self.get(
            url_for("apiv2.topic_elements", topic=topic, q="apprentissage algorithmes")
        )
        assert response.status_code == 200
        assert response.json["total"] == 3
        assert all(elt["id"] in [str(m.id) for m in matches_1] for elt in response.json["data"])

        # Test diacritics - search without accents should match content with accents
        response = self.get(url_for("apiv2.topic_elements", topic=topic, q="systeme donnees"))
        assert response.status_code == 200
        assert response.json["total"] >= 1

        # Test reverse diacritics - search with accents should work
        response = self.get(url_for("apiv2.topic_elements", topic=topic, q="création modèle"))
        assert response.status_code == 200
        assert response.json["total"] >= 1

    def test_elements_list_class_filter(self):
        topic = TopicFactory()
        dataset_elt = TopicElementDatasetFactory(topic=topic)
        reuse_elt = TopicElementReuseFactory(topic=topic)
        no_elt = TopicElementFactory(topic=topic)

        response = self.get(url_for("apiv2.topic_elements", topic=topic, **{"class": "Dataset"}))
        assert response.status_code == 200
        assert response.json["total"] == 1
        assert str(dataset_elt.id) == response.json["data"][0]["id"]

        response = self.get(url_for("apiv2.topic_elements", topic=topic, **{"class": "Reuse"}))
        assert response.status_code == 200
        assert response.json["total"] == 1
        assert str(reuse_elt.id) == response.json["data"][0]["id"]

        response = self.get(url_for("apiv2.topic_elements", topic=topic, **{"class": "None"}))
        assert response.status_code == 200
        assert response.json["total"] == 1
        assert str(no_elt.id) == response.json["data"][0]["id"]

        response = self.get(url_for("apiv2.topic_elements", topic=topic, **{"class": "NotAModel"}))
        assert response.status_code == 200
        assert response.json["total"] == 0

    def test_elements_list_tags_filter(self):
        topic = TopicFactory()
        match_tag = TopicElementFactory(topic=topic, tags=["is-a-match-1", "is-a-match-2"])
        match_tag_2 = TopicElementFactory(topic=topic, tags=["is-a-match-2"])
        no_match_tag = TopicElementFactory(topic=topic, tags=["is-not-a-match"])
        response = self.get(
            url_for("apiv2.topic_elements", topic=topic, tag=["is-a-match-1", "is-a-match-2"])
        )
        assert response.status_code == 200
        assert response.json["total"] == 1
        assert str(match_tag.id) in [elt["id"] for elt in response.json["data"]]
        assert str(no_match_tag.id) not in [elt["id"] for elt in response.json["data"]]
        assert str(match_tag_2.id) not in [elt["id"] for elt in response.json["data"]]

    def test_add_elements(self):
        owner = self.login()
        topic = TopicWithElementsFactory(owner=owner)
        dataset = DatasetFactory()
        reuse = ReuseFactory()
        dataservice = DataserviceFactory()
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
                {
                    "title": "A dataservice",
                    "description": "A dataservice description",
                    "tags": ["tag1", "tag2"],
                    "extras": {"extra": "value"},
                    "element": {"class": "Dataservice", "id": dataservice.id},
                },
                {
                    "title": "An element without element",
                    "description": "An element description",
                    "tags": ["tag1", "tag2"],
                    "extras": {"extra": "value"},
                    "element": None,
                },
            ],
        )
        assert response.status_code == 201

        # Verify response payload contains the created elements
        response_data = response.json
        assert isinstance(response_data, list)
        assert len(response_data) == 4

        # Verify the dataset element in response
        dataset_response = next(
            elem
            for elem in response_data
            if elem["element"] and elem["element"]["id"] == str(dataset.id)
        )
        assert dataset_response["id"] is not None
        assert dataset_response["title"] == "A dataset"
        assert dataset_response["description"] == "A dataset description"
        assert dataset_response["tags"] == ["tag1", "tag2"]
        assert dataset_response["extras"] == {"extra": "value"}
        assert dataset_response["element"]["class"] == "Dataset"

        # Verify the reuse element in response
        reuse_response = next(
            elem
            for elem in response_data
            if elem["element"] and elem["element"]["id"] == str(reuse.id)
        )
        assert reuse_response["id"] is not None
        assert reuse_response["title"] == "A reuse"
        assert reuse_response["description"] == "A reuse description"
        assert reuse_response["tags"] == ["tag1", "tag2"]
        assert reuse_response["extras"] == {"extra": "value"}
        assert reuse_response["element"]["class"] == "Reuse"

        # Verify the element without reference in response
        no_element_response = next(
            elem
            for elem in response_data
            if elem["element"] is None and elem["title"] == "An element without element"
        )
        assert no_element_response["id"] is not None
        assert no_element_response["description"] == "An element description"
        assert no_element_response["tags"] == ["tag1", "tag2"]
        assert no_element_response["extras"] == {"extra": "value"}

        topic.reload()
        assert len(topic.elements) == 8

        dataset_elt = next(
            elt for elt in topic.elements if elt.element and elt.element.id == dataset.id
        )
        assert dataset_elt.title == "A dataset"
        assert dataset_elt.description == "A dataset description"
        assert dataset_elt.tags == ["tag1", "tag2"]
        assert dataset_elt.extras == {"extra": "value"}

        reuse_elt = next(
            elt for elt in topic.elements if elt.element and elt.element.id == reuse.id
        )
        assert reuse_elt.title == "A reuse"
        assert reuse_elt.description == "A reuse description"
        assert reuse_elt.tags == ["tag1", "tag2"]
        assert reuse_elt.extras == {"extra": "value"}

        dataservice_elt = next(
            elt for elt in topic.elements if elt.element and elt.element.id == dataservice.id
        )
        assert dataservice_elt.title == "A dataservice"
        assert dataservice_elt.description == "A dataservice description"
        assert dataservice_elt.tags == ["tag1", "tag2"]
        assert dataservice_elt.extras == {"extra": "value"}

        no_elt_elt = next(
            elt for elt in topic.elements if elt.title == "An element without element"
        )
        assert no_elt_elt.description == "An element description"
        assert no_elt_elt.tags == ["tag1", "tag2"]
        assert no_elt_elt.extras == {"extra": "value"}
        assert no_elt_elt.element is None

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

    def test_clear_elements(self):
        """It should remove all elements from a Topic"""
        owner = self.login()
        topic = TopicWithElementsFactory(owner=owner)
        self.assertGreater(len(topic.elements), 0)
        response = self.delete(url_for("apiv2.topic_elements", topic=topic))
        self.assert204(response)
        topic.reload()
        self.assertEqual(len(topic.elements), 0)

    def test_add_elements_creates_correct_activity(self):
        """It should create 'created' activities when adding elements via POST"""
        owner = self.login()
        topic = TopicFactory(owner=owner)
        dataset = DatasetFactory()

        response = self.post(
            url_for("apiv2.topic_elements", topic=topic),
            [
                {
                    "title": "A dataset",
                    "description": "A dataset description",
                    "element": {"class": "Dataset", "id": dataset.id},
                }
            ],
        )
        assert response.status_code == 201

        created_activities = UserCreatedTopicElement.objects(related_to=topic)
        updated_activities = UserUpdatedTopicElement.objects(related_to=topic)

        assert len(created_activities) == 1
        assert len(updated_activities) == 0

        created_activity = created_activities.first()
        assert created_activity.actor == owner
        assert created_activity.related_to == topic
        assert "element_id" in created_activity.extras

    def test_topic_api_create_with_elements_creates_correct_activities(self):
        """It should create 'created' activities when creating a topic with elements"""
        owner = self.login()
        dataset = DatasetFactory()
        reuse = ReuseFactory()

        data = {
            "name": "Test Topic",
            "description": "A test topic",
            "tags": ["test-tag"],
            "elements": [
                {
                    "title": "A dataset element",
                    "description": "A dataset description",
                    "element": {"class": "Dataset", "id": str(dataset.id)},
                },
                {
                    "title": "A reuse element",
                    "description": "A reuse description",
                    "element": {"class": "Reuse", "id": str(reuse.id)},
                },
                {
                    "title": "An element without reference",
                    "description": "No element reference",
                    "element": None,
                },
            ],
        }

        response = self.post(url_for("apiv2.topics_list"), data)
        self.assert201(response)

        topic = Topic.objects.first()

        created_activities = UserCreatedTopicElement.objects(related_to=topic)
        updated_activities = UserUpdatedTopicElement.objects(related_to=topic)

        assert len(created_activities) == 3
        assert len(updated_activities) == 0

        for activity in created_activities:
            assert activity.actor == owner
            assert activity.related_to == topic
            assert "element_id" in activity.extras


class TopicElementAPITest(APITestCase):
    def test_delete_element(self):
        owner = self.login()
        topic = TopicWithElementsFactory(owner=owner)
        element = topic.elements[0]
        response = self.delete(url_for("apiv2.topic_element", topic=topic, element_id=element.id))
        assert response.status_code == 204
        topic.reload()
        assert len(topic.elements) == 3
        assert element.id not in (elt.id for elt in topic.elements)

    def test_delete_element_perm(self):
        topic = TopicWithElementsFactory(owner=UserFactory())
        element = topic.elements[0]
        self.login()
        response = self.delete(url_for("apiv2.topic_element", topic=topic, element_id=element.id))
        assert response.status_code == 403

    def test_update_element(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        dataset = DatasetFactory()
        element = TopicElementFactory(topic=topic, title="foo")
        response = self.put(
            url_for("apiv2.topic_element", topic=topic, element_id=element.id),
            {
                "title": "bar",
                "description": "baz",
                "tags": ["baz"],
                "extras": {"foo": "bar"},
                "element": {"class": "Dataset", "id": str(dataset.id)},
            },
        )
        assert response.status_code == 200
        assert response.json["title"] == "bar"
        topic.reload()
        assert len(topic.elements) == 1
        element = topic.elements.first()
        assert element.title == "bar"
        assert element.description == "baz"
        assert element.tags == ["baz"]
        assert element.extras == {"foo": "bar"}
        assert element.element.id == dataset.id

    def test_update_element_no_element(self):
        owner = self.login()
        topic = TopicFactory(owner=owner)
        element = TopicElementFactory(topic=topic, title="foo")
        response = self.put(
            url_for("apiv2.topic_element", topic=topic, element_id=element.id),
            {
                "title": "bar",
                "description": "baz",
                "tags": ["baz"],
                "extras": {"foo": "bar"},
                "element": None,
            },
        )
        assert response.status_code == 200
        assert response.json["title"] == "bar"
        assert response.json["element"] is None
        topic.reload()
        assert len(topic.elements) == 1
        element = topic.elements.first()
        assert element.title == "bar"
        assert element.description == "baz"
        assert element.tags == ["baz"]
        assert element.extras == {"foo": "bar"}
        assert element.element is None
