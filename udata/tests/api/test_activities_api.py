import pytest
from flask import url_for
from werkzeug.test import TestResponse

from udata.core.activity.models import Activity
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.reuse.factories import ReuseFactory
from udata.core.reuse.models import Reuse
from udata.core.user.factories import UserFactory
from udata.mongo import db
from udata.tests.helpers import assert200, assert400

pytestmark = [
    pytest.mark.usefixtures("clean_db"),
]


class FakeDatasetActivity(Activity):
    key = "fakeDataset"
    related_to = db.ReferenceField(Dataset, required=True)


class FakeReuseActivity(Activity):
    key = "fakeReuse"
    related_to = db.ReferenceField(Reuse, required=True)


class ActivityAPITest:
    modules = []

    def test_activity_api_list(self, api) -> None:
        """It should fetch an activity list from the API"""
        activities: list[Activity] = [
            FakeDatasetActivity.objects.create(actor=UserFactory(), related_to=DatasetFactory()),
            FakeReuseActivity.objects.create(actor=UserFactory(), related_to=ReuseFactory()),
        ]

        response: TestResponse = api.get(url_for("api.activity"))
        assert200(response)
        assert len(response.json["data"]) == len(activities)

    def test_activity_api_list_filter_by_bogus_related_to(self, api) -> None:
        """It should return a 400 error if the `related_to` parameter isn't a valid ObjectId."""
        response: TestResponse = api.get(url_for("api.activity", related_to="foobar"))
        assert400(response)

    def test_activity_api_list_filtered_by_related_to(self, api) -> None:
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

        response: TestResponse = api.get(url_for("api.activity", related_to=dataset1.id))
        assert200(response)
        len(response.json["data"]) == 2
        assert response.json["data"][0]["related_to"] == dataset1.title
        assert response.json["data"][1]["related_to"] == dataset1.title

        response: TestResponse = api.get(url_for("api.activity", related_to=reuse.id))
        assert200(response)
        len(response.json["data"]) == 1
        assert response.json["data"][0]["related_to"] == reuse.title
