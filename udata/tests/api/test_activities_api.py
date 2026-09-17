from datetime import UTC, datetime

from bson import ObjectId
from flask import url_for
from mongoengine.fields import ReferenceField
from werkzeug.test import TestResponse

from udata.core.activity.models import Activity
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.reuse.models import Reuse
from udata.core.topic.factories import TopicFactory
from udata.core.topic.models import Topic
from udata.core.user.factories import AdminFactory, UserFactory
from udata.core.user.models import User
from udata.harvest.tests.factories import HarvestSourceFactory
from udata.i18n import lazy_gettext as _
from udata.tests.api import APITestCase
from udata.tests.helpers import assert200, assert400


class FakeDatasetActivity(Activity):
    key = "fakeDataset"
    # Lazy, as every real activity label is: it has to be resolved when serialized.
    label = _("did something to a dataset")
    related_to = ReferenceField(Dataset, required=True)


class FakeReuseActivity(Activity):
    key = "fakeReuse"
    related_to = ReferenceField(Reuse, required=True)


class FakeTopicActivity(Activity):
    key = "fakeTopic"
    related_to = ReferenceField(Topic, required=True)


class ActivityAPITest(APITestCase):
    def test_activity_api_list(self) -> None:
        """It should fetch an activity list from the API"""
        activities: list[Activity] = [
            FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=DatasetFactory()),
            FakeReuseActivity.objects.create(actor=UserFactory(), related_to=ReuseFactory()),
        ]

        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == len(activities)

    def test_activity_api_payload_shape(self) -> None:
        """Pins the serialized keys, which the front reads by name."""
        actor: User = UserFactory()
        dataset: Dataset = DatasetFactory()
        activity: Activity = FakeDatasetActivity.objects.create(
            actor=actor, related_to=dataset, changes=["title"], extras={"some": "extra"}
        )
        # Mongo stores milliseconds, so read back the value that is actually serialized.
        activity.reload()

        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)

        data = response.json["data"][0]
        assert data == {
            "id": str(activity.id),
            "actor": {
                "id": str(actor.id),
                "class": "User",
                "slug": actor.slug,
                "first_name": actor.first_name,
                "last_name": actor.last_name,
                "avatar": None,
                "avatar_thumbnail": None,
                "page": actor.self_web_url(),
                "uri": actor.self_api_url(),
            },
            "organization": None,
            "related_to": dataset.title,
            "related_to_id": str(dataset.id),
            "related_to_kind": "Dataset",
            "related_to_url": dataset.self_api_url(),
            "created_at": activity.created_at.replace(tzinfo=UTC).isoformat(),
            "label": str(FakeDatasetActivity.label),
            "key": "fakeDataset",
            "icon": FakeDatasetActivity.icon,
            "changes": ["title"],
            "extras": {"some": "extra"},
        }

    def test_activity_api_list_filter_by_bogus_related_to(self) -> None:
        """It should return a 400 error if the `related_to` parameter isn't a valid ObjectId."""
        response: TestResponse = self.get(url_for("api.activity", related_to="foobar"))
        assert400(response)

    def test_activity_api_list_filter_by_bogus_organization(self) -> None:
        """It should return a 400 error if the `organization` parameter isn't a valid ObjectId."""
        response: TestResponse = self.get(url_for("api.activity", organization="foobar"))
        assert400(response)

    def test_activity_api_list_filtered_by_related_to(self) -> None:
        """It should only return activities that correspond to the `related_to` parameter."""
        dataset1: Dataset = DatasetFactory()
        dataset2: Dataset = DatasetFactory()
        reuse: Reuse = ReuseFactory()
        _activities: list[Activity] = [
            FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=dataset1),
            FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=dataset1),
            FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=dataset2),
            FakeReuseActivity.objects.create(actor=UserFactory(), related_to=reuse),
        ]

        response: TestResponse = self.get(url_for("api.activity", related_to=dataset1.id))
        assert200(response)
        len(response.json["data"]) == 2
        assert response.json["data"][0]["related_to"] == dataset1.title
        assert response.json["data"][1]["related_to"] == dataset1.title

        response: TestResponse = self.get(url_for("api.activity", related_to=reuse.id))
        assert200(response)
        len(response.json["data"]) == 1
        assert response.json["data"][0]["related_to"] == reuse.title

    def test_activity_api_list_filtered_by_user(self) -> None:
        """It should only return activities whose actor is the `user` parameter."""
        actor: User = UserFactory()
        FakeDatasetActivity.objects.create(actor=actor, related_to=DatasetFactory())
        FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=DatasetFactory())

        response: TestResponse = self.get(url_for("api.activity", user=actor.id))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["actor"]["id"] == str(actor.id)
        assert response.json["data"][0]["actor"]["class"] == "User"

    def test_activity_api_list_with_a_non_user_actor(self) -> None:
        """A non-human actor is serialized with its own shape, not as a broken user."""
        source = HarvestSourceFactory()
        FakeDatasetActivity.objects.create(actor=source, related_to=DatasetFactory())

        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)
        assert response.json["data"][0]["actor"] == {
            "id": str(source.id),
            "class": "HarvestSource",
        }

    def test_activity_api_list_filtered_by_unknown_user(self) -> None:
        """An id matching no user matches no activity."""
        FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=DatasetFactory())

        response: TestResponse = self.get(url_for("api.activity", user=ObjectId()))
        assert200(response)
        assert response.json["data"] == []

    def test_activity_api_list_filter_by_bogus_user(self) -> None:
        """It should return a 400 error if the `user` parameter isn't a valid ObjectId."""
        response: TestResponse = self.get(url_for("api.activity", user="foobar"))
        assert400(response)

    def test_activity_api_list_filtered_by_key(self) -> None:
        """It should only return activities whose key is among the `key` parameters."""
        FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=DatasetFactory())
        FakeReuseActivity.objects.create(actor=UserFactory(), related_to=ReuseFactory())
        FakeTopicActivity.objects.create(actor=UserFactory(), related_to=TopicFactory())

        response: TestResponse = self.get(url_for("api.activity", key="fakeDataset"))
        assert200(response)
        assert [activity["key"] for activity in response.json["data"]] == ["fakeDataset"]

        response = self.get(
            url_for("api.activity") + "?key=fakeDataset&key=fakeReuse",
        )
        assert200(response)
        assert sorted(activity["key"] for activity in response.json["data"]) == [
            "fakeDataset",
            "fakeReuse",
        ]

    def test_activity_api_list_filter_by_unknown_key(self) -> None:
        """It should return a 400 error listing the keys it does not know."""
        response: TestResponse = self.get(url_for("api.activity", key="fakeUnicorn"))
        assert400(response)

    def test_activity_api_list_sorted(self) -> None:
        """It should honour the `sort` parameter, most recent first by default."""
        dataset: Dataset = DatasetFactory()
        oldest: Activity = FakeDatasetActivity.objects.create(
            actor=UserFactory(), related_to=dataset, created_at=datetime(2024, 1, 1, tzinfo=UTC)
        )
        newest: Activity = FakeDatasetActivity.objects.create(
            actor=UserFactory(), related_to=dataset, created_at=datetime(2026, 1, 1, tzinfo=UTC)
        )

        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)
        assert [a["created_at"] for a in response.json["data"]] == [
            newest.created_at.isoformat(),
            oldest.created_at.isoformat(),
        ]

        response = self.get(url_for("api.activity", sort="created_at"))
        assert200(response)
        assert [a["created_at"] for a in response.json["data"]] == [
            oldest.created_at.isoformat(),
            newest.created_at.isoformat(),
        ]

    def test_activity_api_list_with_bogus_sort(self) -> None:
        """It should return a 400 error on a sort it does not support."""
        response: TestResponse = self.get(url_for("api.activity", sort="-actor"))
        assert400(response)

    def test_activity_api_list_with_private(self) -> None:
        """It should fetch an activity list from the API"""
        activities: list[Activity] = [
            FakeDatasetActivity.objects.create(
                actor=UserFactory(), related_to=DatasetFactory(private=True)
            ),
            FakeReuseActivity.objects.create(
                actor=UserFactory(), related_to=ReuseFactory(private=True)
            ),
        ]

        # Anonymised user won't see activities about private documents
        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == 0

        # Lambda user won't see activities about private documents
        self.login()
        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == 0

        # Sysadmin user will see activities about private documents
        self.login(AdminFactory())
        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == len(activities)

    def test_activity_api_with_topic(self) -> None:
        """It should fetch topic activities from the API"""
        topic: Topic = TopicFactory()
        FakeTopicActivity.objects.create(actor=UserFactory(), related_to=topic)

        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == 1

        activity_data = response.json["data"][0]
        assert activity_data["related_to"] == topic.name
        assert activity_data["related_to_id"] == str(topic.id)
        assert activity_data["related_to_kind"] == "Topic"
        assert activity_data["related_to_url"] == topic.self_api_url()

    def test_activity_api_list_with_private_visible_to_owner(self) -> None:
        """Owner should see activities about their own private objects."""
        owner = UserFactory()
        dataset = DatasetFactory(private=True, owner=owner)
        FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=dataset)

        # Anonymous user won't see it
        response = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == 0

        # Owner should see their own private dataset activity
        self.login(owner)
        response = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == 1

    def test_activity_api_list_with_private_visible_to_org_member(self) -> None:
        """Organization members should see activities about their org's private objects."""
        member = UserFactory()
        org = OrganizationFactory(admins=[member])
        dataset = DatasetFactory(private=True, organization=org)
        FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=dataset)

        # Anonymous user won't see it
        response = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == 0

        # Org member should see the private dataset activity
        self.login(member)
        response = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == 1

    def test_activity_api_list_with_deleted_actor(self) -> None:
        """It should not crash when an activity actor has been deleted."""
        actor = UserFactory()
        FakeDatasetActivity.objects.create(actor=actor, related_to=DatasetFactory())

        actor.deleted = datetime.now(UTC)
        actor.save()

        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)

    def test_activity_api_list_with_deleted_organization(self) -> None:
        """It should not crash when an activity organization has been deleted."""
        org = OrganizationFactory()
        FakeDatasetActivity.objects.create(
            actor=UserFactory(), related_to=DatasetFactory(), organization=org
        )

        org.deleted = datetime.now(UTC)
        org.save()

        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)

    def test_activity_api_list_with_dangling_related_to(self) -> None:
        """It should not crash when an activity references a deleted object."""
        dataset = DatasetFactory()
        FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=dataset)

        # Simulate a manual/document purge that leaves the activity with a DBRef.
        Dataset._get_collection().delete_one({"_id": dataset.id})

        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == 0

    def test_activity_api_list_with_dangling_actor(self) -> None:
        """It should not crash when an activity actor has been hard-deleted."""
        actor = UserFactory()
        FakeDatasetActivity.objects.create(actor=actor, related_to=DatasetFactory())

        # Simulate a manual hard-delete of the user leaving a dangling DBRef in the activity.
        User._get_collection().delete_one({"_id": actor.id})

        response: TestResponse = self.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == 0
