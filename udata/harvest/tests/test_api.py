import logging
from datetime import UTC, datetime

import pytest
from flask import url_for
from pytest_mock import MockerFixture

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.harvest.backends import get_enabled_backends
from udata.models import Member, PeriodicTask
from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import assert200, assert201, assert204, assert400, assert403, assert404
from udata.utils import faker

from .. import actions
from ..models import (
    VALIDATION_ACCEPTED,
    VALIDATION_PENDING,
    VALIDATION_REFUSED,
    HarvestError,
    HarvestItem,
    HarvestSource,
    HarvestSourceValidation,
)
from .factories import HarvestJobFactory, HarvestSourceFactory, MockBackendsMixin

log = logging.getLogger(__name__)


class HarvestAPITest(MockBackendsMixin, PytestOnlyAPITestCase):
    def test_list_backends(self):
        """It should fetch the harvest backends list from the API"""
        response = self.get(url_for("api.harvest_backends"))
        assert200(response)
        assert len(response.json) == len(get_enabled_backends())
        for data in response.json:
            assert "id" in data
            assert "label" in data
            assert "filters" in data
            assert isinstance(data["filters"], (list, tuple))
            assert "extra_configs" in data

    def test_list_sources(self):
        sources = HarvestSourceFactory.create_batch(3)

        response = self.get(url_for("api.harvest_sources"))
        assert200(response)
        assert len(response.json["data"]) == len(sources)

    def test_list_sources_exclude_deleted(self):
        sources = HarvestSourceFactory.create_batch(3)
        HarvestSourceFactory.create_batch(2, deleted=datetime.now(UTC))

        response = self.get(url_for("api.harvest_sources"))
        assert200(response)
        assert len(response.json["data"]) == len(sources)

    def test_list_sources_include_deleted(self):
        sources = HarvestSourceFactory.create_batch(3)
        sources.extend(HarvestSourceFactory.create_batch(2, deleted=datetime.now(UTC)))

        response = self.get(url_for("api.harvest_sources", deleted=True))
        assert200(response)
        assert len(response.json["data"]) == len(sources)

    def test_list_sources_for_owner(self):
        owner = UserFactory()
        sources = HarvestSourceFactory.create_batch(3, owner=owner)
        HarvestSourceFactory()

        url = url_for("api.harvest_sources", owner=str(owner.id))
        response = self.get(url)
        assert200(response)

        assert len(response.json["data"]) == len(sources)

    def test_list_sources_for_org(self):
        org = OrganizationFactory()
        sources = HarvestSourceFactory.create_batch(3, organization=org)
        HarvestSourceFactory()

        response = self.get(url_for("api.harvest_sources", owner=str(org.id)))
        assert200(response)

        assert len(response.json["data"]) == len(sources)

    def test_list_sources_search(self):
        HarvestSourceFactory.create_batch(3)
        source = HarvestSourceFactory(name="Moissonneur GeoNetwork de la ville de Rennes")

        url = url_for("api.harvest_sources", q="geonetwork rennes")
        response = self.get(url)
        assert200(response)

        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(source.id)

    def test_list_sources_paginate(self):
        total = 25
        page_size = 20
        HarvestSourceFactory.create_batch(total)

        url = url_for("api.harvest_sources", page=1, page_size=page_size)
        response = self.get(url)
        assert200(response)
        assert len(response.json["data"]) == page_size
        assert response.json["total"] == total

        url = url_for("api.harvest_sources", page=2, page_size=page_size)
        response = self.get(url)
        assert200(response)
        assert len(response.json["data"]) == total - page_size
        assert response.json["total"] == total

        url = url_for("api.harvest_sources", page=3, page_size=page_size)
        response = self.get(url)
        assert404(response)

    def test_create_source_with_owner(self):
        """It should create and attach a new source to an owner"""
        user = self.login()
        data = {"name": faker.word(), "url": faker.url(), "backend": "factory"}
        response = self.post(url_for("api.harvest_sources"), data)

        assert201(response)

        source = response.json
        assert source["validation"]["state"] == VALIDATION_PENDING
        assert source["owner"]["id"] == str(user.id)
        assert source["organization"] is None

    def test_create_source_with_org(self):
        """It should create and attach a new source to an organization"""
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "organization": str(org.id),
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert201(response)

        source = response.json
        assert source["validation"]["state"] == VALIDATION_PENDING
        assert source["owner"] is None
        assert source["organization"]["id"] == str(org.id)

    def test_create_source_with_org_not_member(self):
        """It should create and attach a new source to an organization"""
        user = self.login()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "organization": str(org.id),
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert403(response)

    def test_create_source_with_config(self):
        """It should create a new source with configuration"""
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "filters": [
                    {"key": "test", "value": 1},
                    {"key": "test", "value": 42},
                    {"key": "tag", "value": "my-tag"},
                ],
                "features": {
                    "test": True,
                    "toggled": True,
                },
                "extra_configs": [
                    {"key": "test_int", "value": 1},
                    {"key": "test_str", "value": "test"},
                ],
            },
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert201(response)

        source = response.json
        assert source["config"] == {
            "filters": [
                {"key": "test", "value": 1},
                {"key": "test", "value": 42},
                {"key": "tag", "value": "my-tag"},
            ],
            "features": {
                "test": True,
                "toggled": True,
            },
            "extra_configs": [
                {"key": "test_int", "value": 1},
                {"key": "test_str", "value": "test"},
            ],
        }

    def test_create_source_with_unknown_filter(self):
        """Can only use known filters in config"""
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "filters": [
                    {"key": "unknown", "value": "any"},
                ]
            },
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_bad_filter_type(self):
        """Can only use the xpected filter type"""
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "filters": [
                    {"key": "test", "value": "not-an-integer"},
                ]
            },
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_bad_filter_format(self):
        """Filters should have the right format"""
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "filters": [
                    {"key": "unknown", "notvalue": "any"},
                ]
            },
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_unknown_extra_config(self):
        """Can only use known extra config in config"""
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "extra_configs": [
                    {"key": "unknown", "value": "any"},
                ]
            },
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_bad_extra_config_type(self):
        """Can only use the expected extra config type"""
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "extra_configs": [
                    {"key": "test_int", "value": "not-an-integer"},
                ]
            },
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_bad_extra_config_format(self):
        """Extra config should have the right format"""
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "extra_configs": [
                    {"key": "unknown", "notvalue": "any"},
                ]
            },
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_unknown_feature(self):
        """Can only use known features in config"""
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "features": {"unknown": True},
            },
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_false_feature(self):
        """It should handled negative values"""
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "features": {
                    "test": False,
                    "toggled": False,
                }
            },
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert201(response)

        source = response.json
        assert source["config"] == {
            "features": {
                "test": False,
                "toggled": False,
            }
        }

    def test_create_source_with_not_boolean_feature(self):
        """It should handled negative values"""
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "features": {
                    "test": "not a boolean",
                }
            },
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_config_with_custom_key(self):
        self.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {"custom": "value"},
        }
        response = self.post(url_for("api.harvest_sources"), data)

        assert201(response)

        source = response.json
        assert source["config"] == {"custom": "value"}

    def test_update_source(self):
        """It should update a source if owner or orga admin"""
        user = self.login()
        source = HarvestSourceFactory(owner=user)
        new_url = faker.url()
        data = {
            "name": source.name,
            "description": source.description,
            "url": new_url,
            "backend": "factory",
        }
        api_url = url_for("api.harvest_source", source=source)
        response = self.put(api_url, data)
        assert200(response)
        assert response.json["url"] == new_url

        # Source is now owned by orga, with user as admin
        source.organization = OrganizationFactory(members=[Member(user=user, role="admin")])
        source.save()
        api_url = url_for("api.harvest_source", source=source)
        response = self.put(api_url, data)
        assert200(response)

    def test_update_source_require_permission(self):
        """It should not update a source if not the owner"""
        self.login()
        source = HarvestSourceFactory()
        new_url: str = faker.url()
        data = {
            "name": source.name,
            "description": source.description,
            "url": new_url,
            "backend": "factory",
        }
        api_url: str = url_for("api.harvest_source", source=source)
        response = self.put(api_url, data)

        assert403(response)

    def test_validate_source(self):
        """It should allow to validate a source if admin"""
        user = self.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {"state": VALIDATION_ACCEPTED}
        url = url_for("api.validate_harvest_source", source=source)
        response = self.post(url, data)
        assert200(response)

        source.reload()
        assert source.validation.state == VALIDATION_ACCEPTED
        assert source.validation.by == user

    def test_reject_source(self):
        """It should allow to reject a source if admin"""
        user = self.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {"state": VALIDATION_REFUSED, "comment": "Not valid"}
        url = url_for("api.validate_harvest_source", source=source)
        response = self.post(url, data)
        assert200(response)

        source.reload()
        assert source.validation.state == VALIDATION_REFUSED
        assert source.validation.comment == "Not valid"
        assert source.validation.by == user

    def test_validate_source_rejects_unknown_state(self):
        """An unknown `state` value must be rejected with 400, not silently treated as a refusal"""
        self.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {"state": "not_a_real_state", "comment": "anything"}
        response = self.post(url_for("api.validate_harvest_source", source=source), data)
        assert400(response)

        source.reload()
        assert source.validation.state == VALIDATION_PENDING

    def test_reject_source_without_comment_fails(self):
        """Rejection requires a comment (required_if check on the comment field)"""
        self.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {"state": VALIDATION_REFUSED}
        response = self.post(url_for("api.validate_harvest_source", source=source), data)
        assert400(response)

        source.reload()
        assert source.validation.state == VALIDATION_PENDING

    def test_validate_source_is_admin_only(self):
        """It should allow to validate a source if admin"""
        self.login()
        source = HarvestSourceFactory()

        data = {"validate": True}
        url = url_for("api.validate_harvest_source", source=source)
        response = self.post(url, data)
        assert403(response)

    def test_get_source(self):
        source = HarvestSourceFactory()

        url = url_for("api.harvest_source", source=source)
        response = self.get(url)
        assert200(response)

    def test_get_missing_source(self):
        url = url_for("api.harvest_source", source="685bb38b9cb9284b93fd9e72")
        response = self.get(url)
        assert404(response)

    def test_source_preview(self):
        user = self.login()
        source = HarvestSourceFactory(backend="factory", owner=user)

        url = url_for("api.preview_harvest_source", source=source)
        response = self.get(url)
        assert200(response)

    @pytest.mark.options(HARVEST_ENABLE_MANUAL_RUN=True)
    def test_run_source(self, mocker: MockerFixture):
        launch = mocker.patch.object(actions.harvest, "delay")
        user = self.login()

        source = HarvestSourceFactory(
            backend="factory",
            owner=user,
            validation=HarvestSourceValidation(state=VALIDATION_ACCEPTED),
        )

        url = url_for("api.run_harvest_source", source=source)
        response = self.post(url)
        assert200(response)

        launch.assert_called()

    @pytest.mark.options(HARVEST_ENABLE_MANUAL_RUN=False)
    def test_cannot_run_source_if_disabled(self, mocker: MockerFixture):
        launch = mocker.patch.object(actions.harvest, "delay")
        user = self.login()

        source = HarvestSourceFactory(
            backend="factory",
            owner=user,
            validation=HarvestSourceValidation(state=VALIDATION_ACCEPTED),
        )

        url = url_for("api.run_harvest_source", source=source)
        response = self.post(url)
        assert400(response)

        launch.assert_not_called()

    @pytest.mark.options(HARVEST_ENABLE_MANUAL_RUN=True)
    def test_cannot_run_source_if_not_owned(self, mocker: MockerFixture):
        launch = mocker.patch.object(actions.harvest, "delay")
        other_user = UserFactory()
        self.login()

        source = HarvestSourceFactory(
            backend="factory",
            owner=other_user,
            validation=HarvestSourceValidation(state=VALIDATION_ACCEPTED),
        )

        url = url_for("api.run_harvest_source", source=source)
        response = self.post(url)
        assert403(response)

        launch.assert_not_called()

    @pytest.mark.options(HARVEST_ENABLE_MANUAL_RUN=True)
    def test_cannot_run_source_if_not_validated(self, mocker: MockerFixture):
        launch = mocker.patch.object(actions.harvest, "delay")
        user = self.login()

        source = HarvestSourceFactory(
            backend="factory",
            owner=user,
            validation=HarvestSourceValidation(state=VALIDATION_PENDING),
        )

        url = url_for("api.run_harvest_source", source=source)
        response = self.post(url)
        assert400(response)

        launch.assert_not_called()

    def test_source_from_config(self):
        self.login()
        data = {"name": faker.word(), "url": faker.url(), "backend": "factory"}
        response = self.post(url_for("api.preview_harvest_source_config"), data)
        assert200(response)

    def test_delete_source(self):
        user = self.login()
        source = HarvestSourceFactory(owner=user)

        url = url_for("api.harvest_source", source=source)
        response = self.delete(url)
        assert204(response)

        deleted_sources = HarvestSource.objects(deleted__exists=True)
        assert len(deleted_sources) == 1

    def test_delete_source_require_permission(self):
        """It should not delete a source if not the owner"""
        self.login()
        source = HarvestSourceFactory()

        url = url_for("api.harvest_source", source=source)
        response = self.delete(url)

        assert403(response)

    def test_schedule_source(self):
        """It should allow to schedule a source if admin"""
        self.login(AdminFactory())
        source = HarvestSourceFactory()

        data = "0 0 * * *"
        url = url_for("api.schedule_harvest_source", source=source)
        response = self.post(url, data)
        assert200(response)

        assert response.json["schedule"] == "0 0 * * *"

        source.reload()
        assert source.periodic_task is not None
        periodic_task = source.periodic_task
        assert periodic_task.crontab.hour == "0"
        assert periodic_task.crontab.minute == "0"
        assert periodic_task.crontab.day_of_week == "*"
        assert periodic_task.crontab.day_of_month == "*"
        assert periodic_task.crontab.month_of_year == "*"
        assert periodic_task.enabled

    def test_schedule_source_is_admin_only(self):
        """It should only allow admins to schedule a source"""
        self.login()
        source = HarvestSourceFactory()

        data = "0 0 * * *"
        url = url_for("api.schedule_harvest_source", source=source)
        response = self.post(url, data)
        assert403(response)

        source.reload()
        assert source.periodic_task is None

    def test_unschedule_source(self):
        """It should allow to unschedule a source if admin"""
        self.login(AdminFactory())
        periodic_task = PeriodicTask.objects.create(
            task="harvest",
            name=faker.name(),
            description=faker.sentence(),
            enabled=True,
            crontab=PeriodicTask.Crontab(),
        )
        source = HarvestSourceFactory(periodic_task=periodic_task)

        url = url_for("api.schedule_harvest_source", source=source)
        response = self.delete(url)
        assert204(response)

        source.reload()
        assert source.periodic_task is None

    def test_unschedule_source_is_admin_only(self):
        """It should only allow admins to unschedule a source"""
        self.login()
        periodic_task = PeriodicTask.objects.create(
            task="harvest",
            name=faker.name(),
            description=faker.sentence(),
            enabled=True,
            crontab=PeriodicTask.Crontab(),
        )
        source = HarvestSourceFactory(periodic_task=periodic_task)

        url = url_for("api.schedule_harvest_source", source=source)
        response = self.delete(url)
        assert403(response)

        source.reload()
        assert source.periodic_task is not None

    def test_get_job_error_details_hidden_from_non_admin(self):
        """Error `details` (stack traces / internal info) must only be exposed to admins.

        Regression test: before this was fixed, the lambda checked truthiness of the
        `admin_permission` object instead of `.can()`, which leaked details to everyone.
        """
        job = HarvestJobFactory(
            errors=[HarvestError(message="oops", details="secret stack trace")],
        )

        response = self.get(url_for("api.harvest_job", ident=str(job.id)))
        assert200(response)
        assert response.json["errors"][0]["message"] == "oops"
        assert response.json["errors"][0]["details"] is None

        self.login(AdminFactory())
        response = self.get(url_for("api.harvest_job", ident=str(job.id)))
        assert200(response)
        assert response.json["errors"][0]["details"] == "secret stack trace"

    def test_get_job_source_is_a_reference_object(self):
        """A job exposes its source as a {id, class} reference, not a bare string ID.

        This is a contract change vs the v1 API (which returned the source ID as a string).
        Locking it here so the breaking change shows up in the diff if it's ever reverted.
        """
        source = HarvestSourceFactory()
        job = HarvestJobFactory(source=source)

        response = self.get(url_for("api.harvest_job", ident=str(job.id)))
        assert200(response)
        assert response.json["source"] == {
            "id": str(source.id),
            "class": "HarvestSource",
        }

    def test_get_job_items_link(self):
        """A job exposes its items as a paginated subresource link with counters"""
        job = HarvestJobFactory(
            items=[
                HarvestItem(dataset=DatasetFactory()),
                HarvestItem(dataservice=DataserviceFactory()),
                HarvestItem(dataset=DatasetFactory(), remote_url="https://my.remote.example.com"),
            ],
        )
        response = self.get(url_for("api.harvest_job", ident=str(job.id)))
        assert200(response)
        items_link = response.json["items"]
        assert items_link["rel"] == "subsection"
        assert items_link["type"] == "GET"
        assert items_link["href"].endswith(f"/harvest/job/{job.id}/items/")
        assert items_link["total"] == 3
        assert items_link["by_status"] == {
            "pending": 3,
            "started": 0,
            "done": 0,
            "failed": 0,
            "skipped": 0,
            "archived": 0,
        }
        assert items_link["by_type"] == {"dataset": 2, "dataservice": 1}

    def test_list_items(self):
        """It should fetch the harvest items list from the dedicated paginated endpoint"""
        dataset = DatasetFactory()
        dataservice = DataserviceFactory()
        job = HarvestJobFactory(
            items=[
                HarvestItem(dataset=dataset),
                HarvestItem(dataservice=dataservice),
                HarvestItem(dataset=DatasetFactory(), remote_url="https://my.remote.example.com"),
            ],
        )
        response = self.get(url_for("api.harvest_job_items", ident=str(job.id)))
        assert200(response)
        assert response.json["total"] == 3
        assert len(response.json["data"]) == 3
        assert set(response.json["data"][0].keys()) == set(
            [
                "created",
                "started",
                "ended",
                "dataset",
                "dataservice",
                "remote_url",
                "remote_id",
                "args",
                "errors",
                "kwargs",
                "logs",
                "status",
            ]
        )
        # Make sure appropriate dataset or dataservice is set
        assert response.json["data"][0]["dataset"] is not None
        assert response.json["data"][0]["dataservice"] is None
        assert response.json["data"][1]["dataset"] is None
        assert response.json["data"][1]["dataservice"] is not None
        # Make sure remote_url is exposed if exists
        assert response.json["data"][1]["remote_url"] is None
        assert response.json["data"][2]["remote_url"] == "https://my.remote.example.com"

        # Dataset and dataservice references must expose enough info for the frontend
        # to render a link (title + URLs), not just {id, class}.
        dataset_ref = response.json["data"][0]["dataset"]
        assert dataset_ref["id"] == str(dataset.id)
        assert dataset_ref["class"] == "Dataset"
        assert dataset_ref["title"] == dataset.title
        assert dataset_ref["self_web_url"] == dataset.self_web_url()
        assert dataset_ref["self_api_url"] == dataset.self_api_url()

        dataservice_ref = response.json["data"][1]["dataservice"]
        assert dataservice_ref["id"] == str(dataservice.id)
        assert dataservice_ref["class"] == "Dataservice"
        assert dataservice_ref["title"] == dataservice.title
        assert dataservice_ref["self_web_url"] == dataservice.self_web_url()
        assert dataservice_ref["self_api_url"] == dataservice.self_api_url()

    def test_list_items_paginated(self):
        """Items endpoint paginates with page/page_size"""
        job = HarvestJobFactory(items=[HarvestItem() for _ in range(5)])
        response = self.get(
            url_for("api.harvest_job_items", ident=str(job.id), page=2, page_size=2)
        )
        assert200(response)
        assert response.json["total"] == 5
        assert response.json["page"] == 2
        assert response.json["page_size"] == 2
        assert len(response.json["data"]) == 2

    def test_list_items_paginated_links(self):
        """Items endpoint exposes next_page/previous_page URLs at the right places"""
        job = HarvestJobFactory(items=[HarvestItem() for _ in range(5)])

        first = self.get(url_for("api.harvest_job_items", ident=str(job.id), page=1, page_size=2))
        assert200(first)
        assert first.json["previous_page"] is None
        assert "page=2" in first.json["next_page"]

        middle = self.get(url_for("api.harvest_job_items", ident=str(job.id), page=2, page_size=2))
        assert200(middle)
        assert "page=1" in middle.json["previous_page"]
        assert "page=3" in middle.json["next_page"]

        last = self.get(url_for("api.harvest_job_items", ident=str(job.id), page=3, page_size=2))
        assert200(last)
        assert "page=2" in last.json["previous_page"]
        assert last.json["next_page"] is None

    def test_list_items_filtered_by_status(self):
        """Items endpoint accepts a status filter"""
        job = HarvestJobFactory(
            items=[
                HarvestItem(status="done"),
                HarvestItem(status="done"),
                HarvestItem(status="failed"),
                HarvestItem(status="skipped"),
            ],
        )
        response = self.get(url_for("api.harvest_job_items", ident=str(job.id), status="done"))
        assert200(response)
        assert response.json["total"] == 2
        assert {item["status"] for item in response.json["data"]} == {"done"}

        response = self.get(url_for("api.harvest_job_items", ident=str(job.id), status="failed"))
        assert200(response)
        assert response.json["total"] == 1

    def test_list_items_filtered_by_unknown_status(self):
        """Status filter rejects unknown values"""
        job = HarvestJobFactory(items=[HarvestItem()])
        response = self.get(url_for("api.harvest_job_items", ident=str(job.id), status="bogus"))
        assert400(response)

    def test_get_source_permissions_as_anonymous(self):
        """It should return all permissions as False for anonymous users"""
        source = HarvestSourceFactory()

        url = url_for("api.harvest_source", source=source)
        response = self.get(url)
        assert200(response)

        assert "permissions" in response.json
        permissions = response.json["permissions"]
        assert permissions["edit"] is False
        assert permissions["delete"] is False
        assert permissions["run"] is False
        assert permissions["preview"] is False
        assert permissions["validate"] is False
        assert permissions["schedule"] is False

    def test_get_source_permissions_as_owner(self):
        """It should return owner permissions as True for source owner"""
        user = self.login()
        source = HarvestSourceFactory(owner=user)

        url = url_for("api.harvest_source", source=source)
        response = self.get(url)
        assert200(response)

        permissions = response.json["permissions"]
        assert permissions["edit"] is True
        assert permissions["delete"] is True
        assert permissions["run"] is True
        assert permissions["preview"] is True
        assert permissions["validate"] is False
        assert permissions["schedule"] is False

    def test_get_source_permissions_as_org_admin(self):
        """It should return owner permissions as True for org admins"""
        user = self.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        source = HarvestSourceFactory(organization=org)

        url = url_for("api.harvest_source", source=source)
        response = self.get(url)
        assert200(response)

        permissions = response.json["permissions"]
        assert permissions["edit"] is True
        assert permissions["delete"] is True
        assert permissions["run"] is True
        assert permissions["preview"] is True
        assert permissions["validate"] is False
        assert permissions["schedule"] is False

    def test_get_source_permissions_as_org_editor(self):
        """It should return only preview permission as True for org editors"""
        user = self.login()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        source = HarvestSourceFactory(organization=org)

        url = url_for("api.harvest_source", source=source)
        response = self.get(url)
        assert200(response)

        permissions = response.json["permissions"]
        assert permissions["edit"] is False
        assert permissions["delete"] is False
        assert permissions["run"] is False
        assert permissions["preview"] is True
        assert permissions["validate"] is False
        assert permissions["schedule"] is False

    def test_get_source_permissions_as_superadmin(self):
        """It should return all permissions as True for admin users"""
        self.login(AdminFactory())
        source = HarvestSourceFactory()

        url = url_for("api.harvest_source", source=source)
        response = self.get(url)
        assert200(response)

        permissions = response.json["permissions"]
        assert permissions["edit"] is True
        assert permissions["delete"] is True
        assert permissions["run"] is True
        assert permissions["preview"] is True
        assert permissions["validate"] is True
        assert permissions["schedule"] is True

    def test_get_source_permissions_as_other_user(self):
        """It should return all permissions as False for non-owner users"""
        self.login()
        source = HarvestSourceFactory()  # owned by another user

        url = url_for("api.harvest_source", source=source)
        response = self.get(url)
        assert200(response)

        permissions = response.json["permissions"]
        assert permissions["edit"] is False
        assert permissions["delete"] is False
        assert permissions["run"] is False
        assert permissions["preview"] is False
        assert permissions["validate"] is False
        assert permissions["schedule"] is False

    def test_preview_source_require_permission(self):
        """It should not allow preview if not the owner"""
        self.login()
        source = HarvestSourceFactory()  # owned by another user

        url = url_for("api.preview_harvest_source", source=source)
        response = self.get(url)
        assert403(response)
