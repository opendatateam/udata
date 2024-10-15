import logging
from datetime import datetime

import pytest
from flask import url_for
from pytest_mock import MockerFixture

from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.models import Member, PeriodicTask
from udata.tests.helpers import assert200, assert201, assert204, assert400, assert403
from udata.tests.plugin import ApiClient
from udata.utils import faker

from .. import actions
from ..models import (
    VALIDATION_ACCEPTED,
    VALIDATION_PENDING,
    VALIDATION_REFUSED,
    HarvestSource,
    HarvestSourceValidation,
)
from .factories import HarvestSourceFactory, MockBackendsMixin

log = logging.getLogger(__name__)


@pytest.mark.usefixtures("clean_db")
class HarvestAPITest(MockBackendsMixin):
    modules = []

    def test_list_backends(self, api):
        """It should fetch the harvest backends list from the API"""
        response = api.get(url_for("api.harvest_backends"))
        assert200(response)
        assert len(response.json) == len(actions.list_backends())
        for data in response.json:
            assert "id" in data
            assert "label" in data
            assert "filters" in data
            assert isinstance(data["filters"], (list, tuple))
            assert "extra_configs" in data

    def test_list_sources(self, api):
        sources = HarvestSourceFactory.create_batch(3)

        response = api.get(url_for("api.harvest_sources"))
        assert200(response)
        assert len(response.json["data"]) == len(sources)

    def test_list_sources_exclude_deleted(self, api):
        sources = HarvestSourceFactory.create_batch(3)
        HarvestSourceFactory.create_batch(2, deleted=datetime.utcnow())

        response = api.get(url_for("api.harvest_sources"))
        assert200(response)
        assert len(response.json["data"]) == len(sources)

    def test_list_sources_include_deleted(self, api):
        sources = HarvestSourceFactory.create_batch(3)
        sources.extend(HarvestSourceFactory.create_batch(2, deleted=datetime.utcnow()))

        response = api.get(url_for("api.harvest_sources", deleted=True))
        assert200(response)
        assert len(response.json["data"]) == len(sources)

    def test_list_sources_for_owner(self, api):
        owner = UserFactory()
        sources = HarvestSourceFactory.create_batch(3, owner=owner)
        HarvestSourceFactory()

        url = url_for("api.harvest_sources", owner=str(owner.id))
        response = api.get(url)
        assert200(response)

        assert len(response.json["data"]) == len(sources)

    def test_list_sources_for_org(self, api):
        org = OrganizationFactory()
        sources = HarvestSourceFactory.create_batch(3, organization=org)
        HarvestSourceFactory()

        response = api.get(url_for("api.harvest_sources", owner=str(org.id)))
        assert200(response)

        assert len(response.json["data"]) == len(sources)

    def test_create_source_with_owner(self, api):
        """It should create and attach a new source to an owner"""
        user = api.login()
        data = {"name": faker.word(), "url": faker.url(), "backend": "factory"}
        response = api.post(url_for("api.harvest_sources"), data)

        assert201(response)

        source = response.json
        assert source["validation"]["state"] == VALIDATION_PENDING
        assert source["owner"]["id"] == str(user.id)
        assert source["organization"] is None

    def test_create_source_with_org(self, api):
        """It should create and attach a new source to an organization"""
        user = api.login()
        member = Member(user=user, role="admin")
        org = OrganizationFactory(members=[member])
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "organization": str(org.id),
        }
        response = api.post(url_for("api.harvest_sources"), data)

        assert201(response)

        source = response.json
        assert source["validation"]["state"] == VALIDATION_PENDING
        assert source["owner"] is None
        assert source["organization"]["id"] == str(org.id)

    def test_create_source_with_org_not_member(self, api):
        """It should create and attach a new source to an organization"""
        user = api.login()
        member = Member(user=user, role="editor")
        org = OrganizationFactory(members=[member])
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "organization": str(org.id),
        }
        response = api.post(url_for("api.harvest_sources"), data)

        assert403(response)

    def test_create_source_with_config(self, api):
        """It should create a new source with configuration"""
        api.login()
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
        response = api.post(url_for("api.harvest_sources"), data)

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

    def test_create_source_with_unknown_filter(self, api):
        """Can only use known filters in config"""
        api.login()
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
        response = api.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_bad_filter_type(self, api):
        """Can only use the xpected filter type"""
        api.login()
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
        response = api.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_bad_filter_format(self, api):
        """Filters should have the right format"""
        api.login()
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
        response = api.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_unknown_extra_config(self, api):
        """Can only use known extra config in config"""
        api.login()
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
        response = api.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_bad_extra_config_type(self, api):
        """Can only use the expected extra config type"""
        api.login()
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
        response = api.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_bad_extra_config_format(self, api):
        """Extra config should have the right format"""
        api.login()
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
        response = api.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_unknown_feature(self, api):
        """Can only use known features in config"""
        api.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {
                "features": {"unknown": True},
            },
        }
        response = api.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_false_feature(self, api):
        """It should handled negative values"""
        api.login()
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
        response = api.post(url_for("api.harvest_sources"), data)

        assert201(response)

        source = response.json
        assert source["config"] == {
            "features": {
                "test": False,
                "toggled": False,
            }
        }

    def test_create_source_with_not_boolean_feature(self, api):
        """It should handled negative values"""
        api.login()
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
        response = api.post(url_for("api.harvest_sources"), data)

        assert400(response)

    def test_create_source_with_config_with_custom_key(self, api):
        api.login()
        data = {
            "name": faker.word(),
            "url": faker.url(),
            "backend": "factory",
            "config": {"custom": "value"},
        }
        response = api.post(url_for("api.harvest_sources"), data)

        assert201(response)

        source = response.json
        assert source["config"] == {"custom": "value"}

    def test_update_source(self, api):
        """It should update a source if owner or orga member"""
        user = api.login()
        source = HarvestSourceFactory(owner=user)
        new_url = faker.url()
        data = {
            "name": source.name,
            "description": source.description,
            "url": new_url,
            "backend": "factory",
        }
        api_url = url_for("api.harvest_source", ident=str(source.id))
        response = api.put(api_url, data)
        assert200(response)
        assert response.json["url"] == new_url

        # Source is now owned by orga, with user as member
        source.organization = OrganizationFactory(members=[Member(user=user)])
        source.save()
        api_url = url_for("api.harvest_source", ident=str(source.id))
        response = api.put(api_url, data)
        assert200(response)

    def test_update_source_require_permission(self, api):
        """It should not update a source if not the owner"""
        api.login()
        source = HarvestSourceFactory()
        new_url: str = faker.url()
        data = {
            "name": source.name,
            "description": source.description,
            "url": new_url,
            "backend": "factory",
        }
        api_url: str = url_for("api.harvest_source", ident=str(source.id))
        response = api.put(api_url, data)

        assert403(response)

    def test_validate_source(self, api):
        """It should allow to validate a source if admin"""
        user = api.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {"state": VALIDATION_ACCEPTED}
        url = url_for("api.validate_harvest_source", ident=str(source.id))
        response = api.post(url, data)
        assert200(response)

        source.reload()
        assert source.validation.state == VALIDATION_ACCEPTED
        assert source.validation.by == user

    def test_reject_source(self, api):
        """It should allow to reject a source if admin"""
        user = api.login(AdminFactory())
        source = HarvestSourceFactory()

        data = {"state": VALIDATION_REFUSED, "comment": "Not valid"}
        url = url_for("api.validate_harvest_source", ident=str(source.id))
        response = api.post(url, data)
        assert200(response)

        source.reload()
        assert source.validation.state == VALIDATION_REFUSED
        assert source.validation.comment == "Not valid"
        assert source.validation.by == user

    def test_validate_source_is_admin_only(self, api):
        """It should allow to validate a source if admin"""
        api.login()
        source = HarvestSourceFactory()

        data = {"validate": True}
        url = url_for("api.validate_harvest_source", ident=str(source.id))
        response = api.post(url, data)
        assert403(response)

    def test_get_source(self, api):
        source = HarvestSourceFactory()

        url = url_for("api.harvest_source", ident=str(source.id))
        response = api.get(url)
        assert200(response)

    def test_source_preview(self, api):
        api.login()
        source = HarvestSourceFactory(backend="factory")

        url = url_for("api.preview_harvest_source", ident=str(source.id))
        response = api.get(url)
        assert200(response)

    @pytest.mark.options(HARVEST_ENABLE_MANUAL_RUN=True)
    def test_run_source(self, mocker: MockerFixture, api: ApiClient):
        launch = mocker.patch.object(actions.harvest, "delay")
        user = api.login()

        source = HarvestSourceFactory(
            backend="factory",
            owner=user,
            validation=HarvestSourceValidation(state=VALIDATION_ACCEPTED),
        )

        url = url_for("api.run_harvest_source", ident=str(source.id))
        response = api.post(url)
        assert200(response)

        launch.assert_called()

    @pytest.mark.options(HARVEST_ENABLE_MANUAL_RUN=False)
    def test_cannot_run_source_if_disabled(self, mocker: MockerFixture, api: ApiClient):
        launch = mocker.patch.object(actions.harvest, "delay")
        user = api.login()

        source = HarvestSourceFactory(
            backend="factory",
            owner=user,
            validation=HarvestSourceValidation(state=VALIDATION_ACCEPTED),
        )

        url = url_for("api.run_harvest_source", ident=str(source.id))
        response = api.post(url)
        assert400(response)

        launch.assert_not_called()

    @pytest.mark.options(HARVEST_ENABLE_MANUAL_RUN=True)
    def test_cannot_run_source_if_not_owned(self, mocker: MockerFixture, api: ApiClient):
        launch = mocker.patch.object(actions.harvest, "delay")
        other_user = UserFactory()
        api.login()

        source = HarvestSourceFactory(
            backend="factory",
            owner=other_user,
            validation=HarvestSourceValidation(state=VALIDATION_ACCEPTED),
        )

        url = url_for("api.run_harvest_source", ident=str(source.id))
        response = api.post(url)
        assert403(response)

        launch.assert_not_called()

    @pytest.mark.options(HARVEST_ENABLE_MANUAL_RUN=True)
    def test_cannot_run_source_if_not_validated(self, mocker: MockerFixture, api: ApiClient):
        launch = mocker.patch.object(actions.harvest, "delay")
        user = api.login()

        source = HarvestSourceFactory(
            backend="factory",
            owner=user,
            validation=HarvestSourceValidation(state=VALIDATION_PENDING),
        )

        url = url_for("api.run_harvest_source", ident=str(source.id))
        response = api.post(url)
        assert400(response)

        launch.assert_not_called()

    def test_source_from_config(self, api):
        api.login()
        data = {"name": faker.word(), "url": faker.url(), "backend": "factory"}
        response = api.post(url_for("api.preview_harvest_source_config"), data)
        assert200(response)

    def test_delete_source(self, api):
        user = api.login()
        source = HarvestSourceFactory(owner=user)

        url = url_for("api.harvest_source", ident=str(source.id))
        response = api.delete(url)
        assert204(response)

        deleted_sources = HarvestSource.objects(deleted__exists=True)
        assert len(deleted_sources) == 1

    def test_delete_source_require_permission(self, api):
        """It should not delete a source if not the owner"""
        api.login()
        source = HarvestSourceFactory()

        url = url_for("api.harvest_source", ident=str(source.id))
        response = api.delete(url)

        assert403(response)

    def test_schedule_source(self, api):
        """It should allow to schedule a source if admin"""
        api.login(AdminFactory())
        source = HarvestSourceFactory()

        data = "0 0 * * *"
        url = url_for("api.schedule_harvest_source", ident=str(source.id))
        response = api.post(url, data)
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

    def test_schedule_source_is_admin_only(self, api):
        """It should only allow admins to schedule a source"""
        api.login()
        source = HarvestSourceFactory()

        data = "0 0 * * *"
        url = url_for("api.schedule_harvest_source", ident=str(source.id))
        response = api.post(url, data)
        assert403(response)

        source.reload()
        assert source.periodic_task is None

    def test_unschedule_source(self, api):
        """It should allow to unschedule a source if admin"""
        api.login(AdminFactory())
        periodic_task = PeriodicTask.objects.create(
            task="harvest",
            name=faker.name(),
            description=faker.sentence(),
            enabled=True,
            crontab=PeriodicTask.Crontab(),
        )
        source = HarvestSourceFactory(periodic_task=periodic_task)

        url = url_for("api.schedule_harvest_source", ident=str(source.id))
        response = api.delete(url)
        assert204(response)

        source.reload()
        assert source.periodic_task is None

    def test_unschedule_source_is_admin_only(self, api):
        """It should only allow admins to unschedule a source"""
        api.login()
        periodic_task = PeriodicTask.objects.create(
            task="harvest",
            name=faker.name(),
            description=faker.sentence(),
            enabled=True,
            crontab=PeriodicTask.Crontab(),
        )
        source = HarvestSourceFactory(periodic_task=periodic_task)

        url = url_for("api.schedule_harvest_source", ident=str(source.id))
        response = api.delete(url)
        assert403(response)

        source.reload()
        assert source.periodic_task is not None
