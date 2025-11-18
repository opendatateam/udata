from datetime import datetime, timedelta

import feedparser
import pytest
from flask import url_for
from werkzeug.test import TestResponse

import udata.core.organization.constants as org_constants
from udata.core.badges.factories import badge_factory
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.constants import REUSE_TOPICS, REUSE_TYPES
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.models import Follow, Member, Reuse
from udata.tests.api import APITestCase, PytestOnlyAPITestCase
from udata.tests.helpers import (
    assert200,
    assert201,
    assert204,
    assert400,
    assert404,
    assert410,
)
from udata.utils import faker


def reuse_in_response(response: TestResponse, reuse: Reuse) -> bool:
    only_reuse = [r for r in response.json["data"] if r["id"] == str(reuse.id)]
    return len(only_reuse) > 0


class ReuseAPITest(PytestOnlyAPITestCase):
    def test_reuse_api_list(self):
        """It should fetch a reuse list from the API"""
        reuses = ReuseFactory.create_batch(3, visible=True)

        response = self.get(url_for("api.reuses"))
        assert200(response)
        assert len(response.json["data"]) == len(reuses)

    def test_reuse_api_list_with_sorts(self):
        ReuseFactory(title="A", created_at="2024-03-01")
        ReuseFactory(title="B", metrics={"views": 42}, created_at="2024-02-01")
        ReuseFactory(title="C", metrics={"views": 1337}, created_at="2024-05-01")
        ReuseFactory(title="D", created_at="2024-04-01")

        response = self.get(url_for("api.reuses", sort="views"))
        assert200(response)

        assert [reuse["title"] for reuse in response.json["data"]] == ["A", "D", "B", "C"]

        response = self.get(url_for("api.reuses", sort="-views"))
        assert200(response)

        assert [reuse["title"] for reuse in response.json["data"]] == ["C", "B", "D", "A"]

        response = self.get(url_for("api.reuses", sort="created"))
        assert200(response)

        assert [reuse["title"] for reuse in response.json["data"]] == ["B", "A", "D", "C"]

    def test_reuse_api_list_with_filters(self):
        """Should filters reuses results based on query filters"""
        owner = UserFactory()
        org = OrganizationFactory()
        org_public_service = OrganizationFactory()
        org_public_service.add_badge(org_constants.PUBLIC_SERVICE)

        [ReuseFactory(topic="health", type="api") for i in range(2)]

        tag_reuse = ReuseFactory(tags=["my-tag", "other"], topic="health", type="api")
        owner_reuse = ReuseFactory(owner=owner, topic="health", type="api")
        org_reuse = ReuseFactory(organization=org, topic="health", type="api")
        org_reuse_public_service = ReuseFactory(
            organization=org_public_service, topic="health", type="api"
        )
        featured_reuse = ReuseFactory(featured=True, topic="health", type="api")
        topic_reuse = ReuseFactory(topic="transport_and_mobility", type="api")
        type_reuse = ReuseFactory(topic="health", type="application")

        # filter on tag
        response = self.get(url_for("api.reuses", tag="my-tag"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(tag_reuse.id)

        # filter on featured
        response = self.get(url_for("api.reuses", featured="true"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(featured_reuse.id)

        response = self.get(url_for("api.reuses", featured="false"))
        assert200(response)
        # Keep only featured reuses (if any)
        data = [reuse for reuse in response.json["data"] if reuse["featured"]]
        assert len(data) == 0  # It did not return any featured reuse

        # filter on topic
        response = self.get(url_for("api.reuses", topic=topic_reuse.topic))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(topic_reuse.id)

        # filter on type
        response = self.get(url_for("api.reuses", type=type_reuse.type))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(type_reuse.id)

        # filter on owner
        response = self.get(url_for("api.reuses", owner=owner.id))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(owner_reuse.id)

        # filter on organization
        response = self.get(url_for("api.reuses", organization=org.id))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(org_reuse.id)

        response = self.get(url_for("api.reuses", owner="owner-id"))
        assert400(response)

        response = self.get(url_for("api.reuses", organization="org-id"))
        assert400(response)

        # filter on organization badge
        response = self.get(url_for("api.reuses", organization_badge=org_constants.PUBLIC_SERVICE))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(org_reuse_public_service.id)

        response = self.get(url_for("api.reuses", organization_badge="bad-badge"))
        assert400(response)

    def test_reuse_api_list_filter_private(self) -> None:
        """Should filters reuses results based on the `private` filter"""
        user = UserFactory()
        public_reuse: Reuse = ReuseFactory()
        private_reuse: Reuse = ReuseFactory(private=True, owner=user)

        # Only public reuses for non-authenticated user.
        response: TestResponse = self.get(url_for("api.reuses"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert reuse_in_response(response, public_reuse)

        # With an authenticated user.
        self.login(user)
        # all the reuses (by default)
        response = self.get(url_for("api.reuses"))
        assert200(response)
        assert len(response.json["data"]) == 2  # Return everything
        assert reuse_in_response(response, public_reuse)
        assert reuse_in_response(response, private_reuse)

        # only public
        response = self.get(url_for("api.reuses", private="false"))
        assert200(response)
        assert len(response.json["data"]) == 1  # Don't return the private reuse
        assert reuse_in_response(response, public_reuse)

        # only private
        response = self.get(url_for("api.reuses", private="true"))
        assert200(response)
        assert len(response.json["data"]) == 1  # Return only the private
        assert reuse_in_response(response, private_reuse)

    def test_reuse_api_list_filter_private_only_owned_by_user(self) -> None:
        """Should only return private reuses that are owned."""
        user = UserFactory()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        private_owned: Reuse = ReuseFactory(private=True, owner=user)
        private_owned_through_org: Reuse = ReuseFactory(private=True, organization=org)
        private_not_owned: Reuse = ReuseFactory(private=True)

        # Only public reuses for non-authenticated user.
        response: TestResponse = self.get(url_for("api.reuses"))
        assert200(response)
        assert len(response.json["data"]) == 0

        # With an authenticated user.
        self.login(user)
        response = self.get(url_for("api.reuses"))
        assert200(response)
        assert len(response.json["data"]) == 2  # Only the owned reuses
        assert reuse_in_response(response, private_owned)
        assert reuse_in_response(response, private_owned_through_org)
        assert not reuse_in_response(response, private_not_owned)

        # Still no private returned if `private=False`
        response = self.get(url_for("api.reuses", private=False))
        assert200(response)
        assert len(response.json["data"]) == 0

        # Still only return owned private reuses
        response = self.get(url_for("api.reuses", private=True))
        assert200(response)
        assert len(response.json["data"]) == 2  # Only the owned reuses
        assert reuse_in_response(response, private_owned)
        assert reuse_in_response(response, private_owned_through_org)
        assert not reuse_in_response(response, private_not_owned)

    def test_reuse_api_list_filter_private_only_owned_by_user_no_user(self) -> None:
        """Shouldn't return any private reuses for non logged in users."""
        user = UserFactory()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        public_owned: Reuse = ReuseFactory(owner=user)
        public_not_owned: Reuse = ReuseFactory()
        _private_owned: Reuse = ReuseFactory(private=True, owner=user)
        _private_owned_through_org: Reuse = ReuseFactory(private=True, organization=org)
        _private_not_owned: Reuse = ReuseFactory(private=True)

        response: TestResponse = self.get(url_for("api.reuses"))
        assert200(response)
        assert len(response.json["data"]) == 2
        assert reuse_in_response(response, public_owned)
        assert reuse_in_response(response, public_not_owned)

        # Still no private returned if `private=False`
        response = self.get(url_for("api.reuses", private=False))
        assert200(response)
        assert len(response.json["data"]) == 2
        assert reuse_in_response(response, public_owned)
        assert reuse_in_response(response, public_not_owned)

        # Still no private returned if `private=True`
        response = self.get(url_for("api.reuses", private=True))
        assert200(response)
        assert len(response.json["data"]) == 0

    def test_reuse_api_get(self):
        """It should fetch a reuse from the API"""
        reuse = ReuseFactory()
        response = self.get(url_for("api.reuse", reuse=reuse))
        assert200(response)

    def test_reuse_api_get_deleted(self):
        """It should not fetch a deleted reuse from the API and raise 410"""
        reuse = ReuseFactory(deleted=datetime.utcnow())
        response = self.get(url_for("api.reuse", reuse=reuse))
        assert410(response)

    def test_reuse_api_get_deleted_but_authorized(self):
        """It should fetch a deleted reuse from the API if authorized"""
        user = self.login()
        reuse = ReuseFactory(deleted=datetime.utcnow(), owner=user)
        response = self.get(url_for("api.reuse", reuse=reuse))
        assert200(response)

    def test_reuse_api_get_private(self):
        """It should not fetch a private reuse from the API and raise 404"""
        reuse = ReuseFactory(private=True)

        response = self.get(url_for("api.reuse", reuse=reuse))
        assert404(response)

    def test_reuse_api_get_private_but_authorized(self):
        """It should fetch a private reuse from the API if user is authorized"""
        user = self.login()
        reuse = ReuseFactory(owner=user, private=True)

        response = self.get(url_for("api.reuse", reuse=reuse))
        assert200(response)

    def test_reuse_api_create(self):
        """It should create a reuse from the API"""
        data = ReuseFactory.as_dict()
        user = self.login()
        response = self.post(url_for("api.reuses"), data)
        assert201(response)
        assert Reuse.objects.count() == 1

        reuse = Reuse.objects.first()
        assert reuse.owner == user
        assert reuse.organization is None

    def test_reuse_api_create_as_org(self):
        """It should create a reuse as organization from the API"""
        user = self.login()
        data = ReuseFactory.as_dict()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        data["organization"] = str(org.id)
        response = self.post(url_for("api.reuses"), data)
        assert201(response)
        assert Reuse.objects.count() == 1

        reuse = Reuse.objects.first()
        assert reuse.owner is None
        assert reuse.organization == org

    def test_reuse_api_create_as_permissions(self):
        """It should create a reuse as organization from the API

        only if user is member.
        """
        self.login()
        data = ReuseFactory.as_dict()
        org = OrganizationFactory()
        data["organization"] = str(org.id)
        response = self.post(url_for("api.reuses"), data)
        assert400(response)
        assert Reuse.objects.count() == 0

    def test_reuse_api_update(self):
        """It should update a reuse from the API"""
        user = self.login()
        reuse = ReuseFactory(owner=user)
        data = reuse.to_dict()
        data["description"] = "new description"
        response = self.put(url_for("api.reuse", reuse=reuse), data)
        assert200(response)
        assert Reuse.objects.count() == 1
        assert Reuse.objects.first().description == "new description"

    def test_reuse_api_remove_org(self):
        user = self.login()
        reuse = ReuseFactory(owner=user)
        data = reuse.to_dict()
        data["organization"] = None
        response = self.put(url_for("api.reuse", reuse=reuse), data)
        assert200(response)
        assert Reuse.objects.count() == 1
        assert Reuse.objects.first().organization is None

    def test_reuse_api_update_org_with_full_object(self):
        """We can send the full org object (not only the ID) to update to an org"""
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        reuse = ReuseFactory(organization=org)

        data = reuse.to_dict()
        data["owner"] = None
        data["organization"] = org.to_dict()

        response = self.put(url_for("api.reuse", reuse=reuse), data)
        assert200(response)

        assert Reuse.objects.count() == 1
        assert Reuse.objects.first().owner is None
        assert Reuse.objects.first().organization.id == org.id

    def test_reuse_api_update_deleted(self):
        """It should not update a deleted reuse from the API and raise 410"""
        self.login()
        reuse = ReuseFactory(deleted=datetime.utcnow())
        response = self.put(url_for("api.reuse", reuse=reuse), {})
        assert410(response)

    def test_reuse_api_delete(self):
        """It should delete a reuse from the API"""
        user = self.login()
        reuse = ReuseFactory(owner=user)
        response = self.delete(url_for("api.reuse", reuse=reuse))
        assert204(response)
        assert Reuse.objects.count() == 1
        assert Reuse.objects[0].deleted is not None

        response = self.put(url_for("api.reuse", reuse=reuse), {"deleted": None})
        assert200(response)
        assert Reuse.objects.count() == 1
        assert Reuse.objects[0].deleted is None

    def test_reuse_api_delete_deleted(self):
        """It should not delete a deleted reuse from the API and raise 410"""
        self.login()
        reuse = ReuseFactory(deleted=datetime.utcnow())
        response = self.delete(url_for("api.reuse", reuse=reuse))
        assert410(response)

    def test_reuse_api_filter_by_dataset(self):
        user = self.login()
        dataset = DatasetFactory()
        other_dataset = DatasetFactory()
        ReuseFactory(owner=user, datasets=[dataset])

        response = self.get(url_for("api.reuses", dataset=dataset.id))
        assert200(response)
        assert response.json["total"] == 1
        assert len(response.json["data"][0]["datasets"]) == 1
        assert response.json["data"][0]["datasets"][0]["title"] == dataset.title

        response = self.get(url_for("api.reuses", dataset=other_dataset.id))
        assert200(response)
        assert response.json["total"] == 0

    def test_reuse_api_add_dataset(self):
        """It should add a dataset to a reuse from the API"""
        user = self.login()
        reuse = ReuseFactory(owner=user)

        dataset = DatasetFactory()
        data = {"id": dataset.id, "class": "Dataset"}
        url = url_for("api.reuse_add_dataset", reuse=reuse)
        response = self.post(url, data)
        assert201(response)
        reuse.reload()
        assert len(reuse.datasets) == 1
        assert reuse.datasets[-1] == dataset

        dataset = DatasetFactory()
        data = {"id": dataset.id, "class": "Dataset"}
        url = url_for("api.reuse_add_dataset", reuse=reuse)
        response = self.post(url, data)
        assert201(response)
        reuse.reload()
        assert len(reuse.datasets) == 2
        assert reuse.datasets[-1] == dataset

    def test_reuse_api_add_dataset_twice(self):
        """It should not add twice a dataset to a reuse from the API"""
        user = self.login()
        dataset = DatasetFactory()
        reuse = ReuseFactory(owner=user, datasets=[dataset])

        data = {"id": dataset.id, "class": "Dataset"}
        url = url_for("api.reuse_add_dataset", reuse=reuse)
        response = self.post(url, data)
        assert200(response)
        reuse.reload()
        assert len(reuse.datasets) == 1
        assert reuse.datasets[-1] == dataset

    def test_reuse_api_add_dataset_not_found(self):
        """It should return 404 when adding an unknown dataset to a reuse"""
        user = self.login()
        reuse = ReuseFactory(owner=user)

        data = {"id": "not-found", "class": "Dataset"}
        url = url_for("api.reuse_add_dataset", reuse=reuse)
        response = self.post(url, data)

        assert404(response)
        reuse.reload()
        assert len(reuse.datasets) == 0

    def test_reuse_api_filter_by_dataservice(self):
        user = self.login()
        dataservice = DataserviceFactory()
        other_dataservice = DataserviceFactory()
        ReuseFactory(owner=user, dataservices=[dataservice])

        response = self.get(url_for("api.reuses", dataservice=dataservice.id))
        assert200(response)
        assert response.json["total"] == 1
        assert len(response.json["data"][0]["dataservices"]) == 1
        assert response.json["data"][0]["dataservices"][0]["title"] == dataservice.title

        response = self.get(url_for("api.reuses", dataservice=other_dataservice.id))
        assert200(response)
        assert response.json["total"] == 0

    def test_reuse_api_add_dataservice(self):
        """It should add a dataset to a reuse from the API"""
        user = self.login()
        reuse = ReuseFactory(owner=user)

        dataservice = DataserviceFactory()
        data = {"id": dataservice.id, "class": "Dataservice"}
        url = url_for("api.reuse_add_dataservice", reuse=reuse)
        response = self.post(url, data)
        assert201(response)
        reuse.reload()
        assert len(reuse.dataservices) == 1
        assert reuse.dataservices[-1] == dataservice

        dataservice = DataserviceFactory()
        data = {"id": dataservice.id, "class": "dataservice"}
        url = url_for("api.reuse_add_dataservice", reuse=reuse)
        response = self.post(url, data)
        assert201(response)
        reuse.reload()
        assert len(reuse.dataservices) == 2
        assert reuse.dataservices[-1] == dataservice

    def test_reuse_api_add_dataservice_twice(self):
        """It should not add twice a dataservice to a reuse from the API"""
        user = self.login()
        dataservice = DataserviceFactory()
        reuse = ReuseFactory(owner=user, dataservices=[dataservice])

        data = {"id": dataservice.id, "class": "Dataservice"}
        url = url_for("api.reuse_add_dataservice", reuse=reuse)
        response = self.post(url, data)
        assert200(response)
        reuse.reload()
        assert len(reuse.dataservices) == 1
        assert reuse.dataservices[-1] == dataservice

    def test_reuse_api_add_dataservice_not_found(self):
        """It should return 404 when adding an unknown dataservice to a reuse"""
        user = self.login()
        reuse = ReuseFactory(owner=user)

        data = {"id": "not-found", "class": "Dataservice"}
        url = url_for("api.reuse_add_dataservice", reuse=reuse)
        response = self.post(url, data)

        assert404(response)
        reuse.reload()
        assert len(reuse.dataservices) == 0

    def test_reuse_api_feature(self):
        """It should mark the reuse featured on POST"""
        reuse = ReuseFactory(featured=False)

        with self.api_user(AdminFactory()):
            response = self.post(url_for("api.reuse_featured", reuse=reuse))
        assert200(response)

        reuse.reload()
        assert reuse.featured

    def test_reuse_api_feature_already(self):
        """It shouldn't do anything to feature an already featured reuse"""
        reuse = ReuseFactory(featured=True)

        with self.api_user(AdminFactory()):
            response = self.post(url_for("api.reuse_featured", reuse=reuse))
        assert200(response)

        reuse.reload()
        assert reuse.featured

    def test_reuse_api_unfeature(self):
        """It should mark the reuse featured on POST"""
        reuse = ReuseFactory(featured=True)

        with self.api_user(AdminFactory()):
            response = self.delete(url_for("api.reuse_featured", reuse=reuse))
        assert200(response)

        reuse.reload()
        assert not reuse.featured

    def test_reuse_api_unfeature_already(self):
        """It shouldn't do anything to unfeature a not featured reuse"""
        reuse = ReuseFactory(featured=False)

        with self.api_user(AdminFactory()):
            response = self.delete(url_for("api.reuse_featured", reuse=reuse))
        assert200(response)

        reuse.reload()
        assert not reuse.featured

    def test_follow_reuse(self):
        """It should follow a reuse on POST"""
        user = self.login()
        to_follow = ReuseFactory()

        response = self.post(url_for("api.reuse_followers", id=to_follow.id))
        assert201(response)

        to_follow.count_followers()
        assert to_follow.get_metrics()["followers"] == 1

        assert Follow.objects.following(to_follow).count() == 0
        assert Follow.objects.followers(to_follow).count() == 1
        follow = Follow.objects.followers(to_follow).first()
        assert isinstance(follow.following, Reuse)
        assert Follow.objects.following(user).count() == 1
        assert Follow.objects.followers(user).count() == 0

    def test_unfollow_reuse(self):
        """It should unfollow the reuse on DELETE"""
        user = self.login()
        to_follow = ReuseFactory()
        Follow.objects.create(follower=user, following=to_follow)

        response = self.delete(url_for("api.reuse_followers", id=to_follow.id))
        assert200(response)

        nb_followers = Follow.objects.followers(to_follow).count()

        assert response.json["followers"] == nb_followers

        assert Follow.objects.following(to_follow).count() == 0
        assert nb_followers == 0
        assert Follow.objects.following(user).count() == 0
        assert Follow.objects.followers(user).count() == 0

    def test_suggest_reuses_api(self):
        """It should suggest reuses"""
        for i in range(3):
            ReuseFactory(
                title="arealtestprefix-{0}".format(i) if i % 2 else faker.word(),
                visible=True,
                metrics={"followers": i},
            )
        max_follower_reuse = ReuseFactory(
            title="arealtestprefix-4", visible=True, metrics={"followers": 10}
        )

        response = self.get(url_for("api.suggest_reuses", q="arealtestpref", size=5))
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert "id" in suggestion
            assert "slug" in suggestion
            assert "title" in suggestion
            assert "image_url" in suggestion
            assert "test" in suggestion["title"]
        assert response.json[0]["id"] == str(max_follower_reuse.id)

    def test_suggest_reuses_api_unicode(self):
        """It should suggest reuses with special characters"""
        for i in range(4):
            ReuseFactory(title="testé-{0}".format(i) if i % 2 else faker.word(), visible=True)

        response = self.get(url_for("api.suggest_reuses", q="testé", size=5))
        assert200(response)

        assert len(response.json) <= 5
        assert len(response.json) > 1

        for suggestion in response.json:
            assert "id" in suggestion
            assert "slug" in suggestion
            assert "title" in suggestion
            assert "image_url" in suggestion
            assert "test" in suggestion["title"]

    def test_suggest_reuses_api_no_match(self):
        """It should not provide reuse suggestion if no match"""
        ReuseFactory.create_batch(3, visible=True)

        response = self.get(url_for("api.suggest_reuses", q="xxxxxx", size=5))
        assert200(response)
        assert len(response.json) == 0

    def test_suggest_reuses_api_empty(self):
        """It should not provide reuse suggestion if no data"""
        # self.init_search()
        response = self.get(url_for("api.suggest_reuses", q="xxxxxx", size=5))
        assert200(response)
        assert len(response.json) == 0


class ReusesFeedAPItest(APITestCase):
    @pytest.mark.options(DELAY_BEFORE_APPEARING_IN_RSS_FEED=10)
    def test_recent_feed(self):
        # We have a 10 hours delay for a new object to appear in feed. A newly created one shouldn't appear.
        ReuseFactory(title="A", datasets=[DatasetFactory()], created_at=datetime.utcnow())
        ReuseFactory(
            title="B", datasets=[DatasetFactory()], created_at=datetime.utcnow() - timedelta(days=2)
        )
        ReuseFactory(
            title="C", datasets=[DatasetFactory()], created_at=datetime.utcnow() - timedelta(days=1)
        )

        response = self.get(url_for("api.recent_reuses_atom_feed"))
        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 2)
        self.assertEqual(feed.entries[0].title, "C")
        self.assertEqual(feed.entries[1].title, "B")

    @pytest.mark.options(DELAY_BEFORE_APPEARING_IN_RSS_FEED=0)
    def test_recent_feed_owner(self):
        owner = UserFactory()
        ReuseFactory(owner=owner, datasets=[DatasetFactory()])

        response = self.get(url_for("api.recent_reuses_atom_feed"))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, owner.fullname)
        self.assertEqual(author.href, owner.url_for())

    @pytest.mark.options(DELAY_BEFORE_APPEARING_IN_RSS_FEED=0)
    def test_recent_feed_org(self):
        owner = UserFactory()
        org = OrganizationFactory()
        ReuseFactory(owner=owner, organization=org, datasets=[DatasetFactory()])

        response = self.get(url_for("api.recent_reuses_atom_feed"))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, org.name)
        self.assertEqual(author.href, org.url_for())


class ReuseBadgeAPITest(PytestOnlyAPITestCase):
    @pytest.fixture(autouse=True)
    def setup_func(self):
        # Register at least two badges
        Reuse.__badges__["test-1"] = "Test 1"
        Reuse.__badges__["test-2"] = "Test 2"

        self.factory = badge_factory(Reuse)
        self.user = self.login(AdminFactory())
        self.reuse = ReuseFactory()

    def test_list(self):
        response = self.get(url_for("api.available_reuse_badges"))
        assert200(response)
        assert len(response.json) == len(Reuse.__badges__)
        for kind, label in Reuse.__badges__.items():
            assert kind in response.json
            assert response.json[kind] == label

    def test_create(self):
        data = self.factory.as_dict()
        response = self.post(url_for("api.reuse_badges", reuse=self.reuse), data)
        assert201(response)
        self.reuse.reload()
        assert len(self.reuse.badges) == 1

    def test_create_same(self):
        data = self.factory.as_dict()
        self.post(url_for("api.reuse_badges", reuse=self.reuse), data)
        response = self.post(url_for("api.reuse_badges", reuse=self.reuse), data)
        assert200(response)
        self.reuse.reload()
        assert len(self.reuse.badges) == 1

    def test_create_2nd(self):
        # Explicitely setting the kind to avoid collisions given the
        # small number of choices for kinds.
        kinds_keys = list(Reuse.__badges__)
        self.reuse.add_badge(kinds_keys[0])
        data = self.factory.as_dict()
        data["kind"] = kinds_keys[1]
        response = self.post(url_for("api.reuse_badges", reuse=self.reuse), data)
        assert201(response)
        self.reuse.reload()
        assert len(self.reuse.badges) == 2

    def test_delete(self):
        badge = self.factory()
        self.reuse.add_badge(badge.kind)
        response = self.delete(
            url_for("api.reuse_badge", reuse=self.reuse, badge_kind=str(badge.kind))
        )
        assert204(response)
        self.reuse.reload()
        assert len(self.reuse.badges) == 0

    def test_delete_404(self):
        response = self.delete(
            url_for("api.reuse_badge", reuse=self.reuse, badge_kind=str(self.factory().kind))
        )
        assert404(response)


class ReuseReferencesAPITest(PytestOnlyAPITestCase):
    def test_reuse_types_list(self):
        """It should fetch the reuse types list from the API"""
        response = self.get(url_for("api.reuse_types"))
        assert200(response)
        assert len(response.json) == len(REUSE_TYPES)

    def test_reuse_topics_list(self):
        """It should fetch the reuse topics list from the API"""
        response = self.get(url_for("api.reuse_topics"))
        assert200(response)
        assert len(response.json) == len(REUSE_TOPICS)
