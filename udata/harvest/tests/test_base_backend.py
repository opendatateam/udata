import logging
from abc import ABC
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from urllib.parse import urlparse

import pytest
import requests
from mongoengine import pre_save
from pytest_mock import MockerFixture
from typing_extensions import override
from voluptuous import Schema

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataset import tasks
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.harvest import HarvestMetadata
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.harvest.models import Harvestable, HarvestItem, HarvestJob
from udata.harvest.signals import after_harvest_job, before_harvest_job
from udata.ssrf import BlockedAddressError
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.helpers import argvalues, assert_equal_dates
from udata.utils import faker

from ..backends import (
    BaseBackend,
    HarvestExtraConfig,
    HarvestFeature,
    HarvestFilter,
    get_all_backends,
)
from ..exceptions import HarvestException, HarvestSkipException, HarvestValidationError
from .factories import HarvestSourceFactory


class Unknown:
    pass


log = logging.getLogger(__name__)


ITEM_LOG_MESSAGE = "Something worth reporting happened while processing this item"


class HarvestLogs:
    """Captures the log level the backend reported a failure with.

    Sentry's logging integration turns `log.exception` into an event, while
    `log.warning` and below stay breadcrumbs: the level *is* the routing.
    """

    def __init__(self, mocker):
        self.info = mocker.patch("udata.harvest.backends.base.log.info")
        self.warning = mocker.patch("udata.harvest.backends.base.log.warning")
        self.exception = mocker.patch("udata.harvest.backends.base.log.exception")

    def assert_not_sent_to_sentry(self):
        self.exception.assert_not_called()

    def assert_sent_to_sentry(self):
        self.exception.assert_called_once()


@pytest.fixture
def harvest_logs(mocker):
    return HarvestLogs(mocker)


def gen_remote_IDs(num: int, prefix: str = "") -> list[str]:
    """Generate remote IDs."""
    return [f"{prefix}fake-{i}" for i in range(num)]


H = TypeVar("H", bound=Harvestable)


@dataclass(frozen=True)
class MockError(ABC):
    exception: Exception


@dataclass(frozen=True)
class MockHarvestError(MockError):
    pass


@dataclass(frozen=True)
class MockRecordError(MockError):
    @property
    def remote_id(self):
        return str(self.exception)


class MockBackend(BaseBackend):
    name = "mock-backend"
    display_name = "Mock Backend"

    filters = (
        HarvestFilter("First filter", "first", str),
        HarvestFilter("Second filter", "second", str),
    )
    features = (
        HarvestFeature("feature", "A test feature"),
        HarvestFeature("enabled", "A test feature enabled by default", default=True),
    )
    extra_configs = (
        HarvestExtraConfig("Test Int", "test_int", int, "An integer"),
        HarvestExtraConfig("Test Str", "test_str", str),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_items: Sequence[Harvestable | MockHarvestError | MockRecordError] = []
        self.mock_last_modified: datetime | None = None

    @override
    def inner_harvest(self):
        for i, mock_item in enumerate(self.mock_items):
            if isinstance(mock_item, MockHarvestError):
                raise mock_item.exception
            # if not hasattr(mock_item, "remote_id"):
            #     pytest.fail(f"mock item {i} has no remote_id, set it via its factory")
            remote_id = getattr(mock_item, "remote_id", None)
            self.process_item(remote_id, self.item_processor, mock_item)

    def item_processor(self, harvest_item: HarvestItem, mock_item: H | MockRecordError) -> H:
        if isinstance(mock_item, MockRecordError):
            raise mock_item.exception
        # TODO: option to call get_item vs return item directly?
        item = self.get_item(harvest_item.remote_id, type(mock_item))
        for name in mock_item._fields:
            if name != "id" and (value := getattr(mock_item, name)) is not None:
                setattr(item, name, value)
        # FIXME: do it in factory?
        item.harvest.remote_url = f"http://www.example.com/records/{harvest_item.remote_id}"
        return item


class MockFetchingBackend(MockBackend):
    """A backend that really goes over the network, to exercise the HTTP layer."""

    name = "mock-fetching-backend"

    def inner_harvest(self):
        self.get(self.source.url).raise_for_status()


# class FailingBackend(MockBackend):
#     """A backend whose harvest raises a configured exception."""

#     name = "failing-backend"
#     exception: Exception

#     def inner_harvest(self):
#         raise self.exception


# class FailingItemBackend(MockBackend):
#     """A backend whose item processing raises a configured exception."""

#     name = "failing-item-backend"
#     exception: Exception

#     def inner_process_dataset(self, item: HarvestItem):
#         raise self.exception

#     def inner_process_dataservice(self, item: HarvestItem):
#         raise self.exception


# class LoggingItemBackend(MockBackend):
#     """A backend logging while processing an item."""

#     name = "logging-item-backend"

#     def inner_process_dataset(self, item: HarvestItem):
#         log.info(ITEM_LOG_MESSAGE)
#         return super().inner_process_dataset(item)

#     def inner_process_dataservice(self, item: HarvestItem):
#         log.info(ITEM_LOG_MESSAGE)
#         return super().inner_process_dataservice(item)


# class InvalidResourceBackend(MockBackend):
#     """A backend harvesting a resource URL the Dataset model refuses."""

#     name = "invalid-resource-backend"

#     def inner_process_dataset(self, item: HarvestItem):
#         dataset = super().inner_process_dataset(item)
#         # A Windows UNC path where an URL is expected, as met on a real catalog.
#         dataset.resources = [
#             ResourceFactory(url="//diffuweb.example.com\\OpenData\\dictionnaire.xlsx")
#         ]
#         return dataset


class HarvestFilterTest:
    @pytest.mark.parametrize("type,expected", HarvestFilter.TYPES.items())
    def test_type_ok(self, type, expected):
        label = faker.word()
        key = faker.word()
        description = faker.sentence()
        hf = HarvestFilter(label, key, type, description)
        assert hf.as_dict() == {
            "label": label,
            "key": key,
            "type": expected,
            "description": description,
        }

    @pytest.mark.parametrize("type", [dict, list, tuple, Unknown])
    def test_type_ko(self, type):
        with pytest.raises(TypeError):
            HarvestFilter(faker.word(), faker.word(), type, faker.sentence())


class BaseBackendTest(PytestOnlyDBTestCase):
    def test_simple_harvest(self):
        nb_datasets = 3
        source = HarvestSourceFactory()
        backend = MockBackend(source)
        backend.mock_items = DatasetFactory.build_batch(
            nb_datasets,
            timestamps=False,
            remote_id=lambda id: f"dataset-{id}",
        )

        before = datetime.now(UTC)
        job = backend.harvest()
        after = datetime.now(UTC)

        assert len(job.items) == nb_datasets
        assert Dataset.objects.count() == nb_datasets
        before_naive = before.replace(tzinfo=None)
        after_naive = after.replace(tzinfo=None)
        for dataset, mock_dataset in zip(Dataset.objects(), backend.mock_items):
            # MongoEngine returns naive datetimes, so normalize before comparison
            last_modified_naive = (
                dataset.last_modified.replace(tzinfo=None)
                if dataset.last_modified.tzinfo
                else dataset.last_modified
            )
            last_update_naive = (
                dataset.harvest.last_update.replace(tzinfo=None)
                if dataset.harvest.last_update.tzinfo
                else dataset.harvest.last_update
            )
            assert before_naive <= last_modified_naive <= after_naive
            assert before_naive <= last_update_naive <= after_naive
            assert dataset.harvest.source_id == str(source.id)
            assert dataset.harvest.domain == source.domain
            assert dataset.harvest.remote_id.startswith("dataset-")

    def test_has_feature_defaults(self):
        backend = MockBackend(HarvestSourceFactory())
        assert not backend.has_feature("feature")
        assert backend.has_feature("enabled")

    def test_has_feature_defined(self):
        backend = MockBackend(
            HarvestSourceFactory(
                config={
                    "features": {
                        "feature": True,
                        "enabled": False,
                    }
                }
            )
        )
        assert backend.has_feature("feature")
        assert not backend.has_feature("enabled")

    def test_has_feature_unkown(self):
        backend = MockBackend(HarvestSourceFactory())
        with pytest.raises(HarvestException):
            backend.has_feature("unknown")

    def test_get_filters_empty(self):
        backend = MockBackend(HarvestSourceFactory())
        assert backend.get_filters() == []

    def test_get_filters(self):
        backend = MockBackend(
            HarvestSourceFactory(
                config={
                    "filters": [
                        {"key": "second", "value": ""},
                        {"key": "first", "value": ""},
                    ]
                }
            )
        )
        assert [f["key"] for f in backend.get_filters()] == ["second", "first"]

    def test_get_extra_config_not_in_source(self):
        backend = MockBackend(HarvestSourceFactory())
        assert backend.get_extra_config_value("test_str") is None

    def test_get_extra_config_value(self):
        backend = MockBackend(
            HarvestSourceFactory(
                config={
                    "extra_configs": [
                        {"key": "test_str", "value": "test"},
                    ]
                }
            )
        )
        assert backend.get_extra_config_value("test_str") == "test"

    @pytest.mark.parametrize("method", ["head", "get", "post"])
    def test_disallows_redirect(self, rmock, method):
        backend = MockBackend(HarvestSourceFactory())
        url = "https://www.url.with.redirect.com/"
        getattr(rmock, method)(url, status_code=302)
        with pytest.raises(requests.exceptions.HTTPError):
            if method == "post":
                getattr(backend, method)(url, data={})
            else:
                getattr(backend, method)(url)

    @pytest.mark.parametrize("method", ["head", "get", "post"])
    def test_refuses_to_fetch_a_private_address(self, method):
        # Deliberately no rmock: requests_mock substitutes the session adapter,
        # which is precisely the guard under test. Nothing needs to listen on the
        # address either — it is rejected before connect().
        backend = MockBackend(HarvestSourceFactory())
        url = "http://10.0.0.1/catalog"
        with pytest.raises(BlockedAddressError, match="private"):
            if method == "post":
                backend.post(url, data={})
            else:
                getattr(backend, method)(url)

    def test_harvest_a_private_address_fails_the_job(self):
        # BlockedAddressError is neither a RequestException nor an OSError (so
        # that urllib3 cannot swallow it): make sure it still lands as a job
        # failure instead of escaping the harvest task.
        source = HarvestSourceFactory()
        # Assigned without saving: URLField keeps a private address out of the
        # stored value, so the case left to exercise is the one it cannot catch
        # — a source whose URL only reaches a forbidden address at fetch time.
        source.url = "http://10.0.0.1/catalog"

        job = MockFetchingBackend(source).harvest()

        assert job.status == "failed"
        assert "10.0.0.1" in job.errors[0].message

    def test_harvest_item_remote_url(self):
        n = 3
        backend = MockBackend(HarvestSourceFactory())
        backend.mock_items = DatasetFactory.build_batch(
            n, remote_id=True
        ) + DataserviceFactory.build_batch(n, remote_id=True)

        job = backend.harvest()

        assert len(job.items) == 2 * n
        assert all([item.remote_url for item in job.items])

    def test_harvest_source_id(self):
        nb_datasets = 3
        source = HarvestSourceFactory()
        backend = MockBackend(source)
        backend.mock_items = DatasetFactory.build_batch(nb_datasets, remote_id=True)

        job = backend.harvest()

        assert len(job.items) == nb_datasets

        source_url = faker.url()
        source.url = source_url
        source.save()

        job = backend.harvest()

        datasets = Dataset.objects()
        # no new datasets have been created
        assert len(datasets) == nb_datasets
        for dataset in datasets:
            assert dataset.harvest.source_id == str(source.id)
            parsed = urlparse(source_url).netloc.split(":")[0]
            assert parsed == dataset.harvest.domain

    def test_dont_overwrite_last_modified(self):
        last_modified = faker.date_time_between(start_date="-30y", end_date="-1y")
        backend = MockBackend(HarvestSourceFactory())
        backend.mock_items = DatasetFactory.build_batch(
            1, remote_id=True, last_modified_internal=last_modified
        )

        backend.harvest()

        dataset = Dataset.objects.first()
        assert_equal_dates(dataset.last_modified_internal, last_modified)
        assert_equal_dates(dataset.harvest.last_update, datetime.now(UTC))

    def test_dont_overwrite_last_modified_even_if_set_to_same(self):
        last_modified = faker.date_time_between(start_date="-30y", end_date="-1y")
        backend = MockBackend(HarvestSourceFactory())
        backend.mock_items = DatasetFactory.build_batch(
            1, remote_id=True, last_modified_internal=last_modified
        )

        backend.harvest()
        # FIXME: double-harvest isn't really supported
        backend.harvest()  # Harvest twice to test same last_modified

        dataset = Dataset.objects.first()
        assert_equal_dates(dataset.last_modified_internal, last_modified)
        assert_equal_dates(dataset.harvest.last_update, datetime.now(UTC))

    def test_autoarchive(self, app):
        grace_days = app.config["HARVEST_AUTOARCHIVE_GRACE_DAYS"]
        nb_datasets = 3
        nb_dataservices = 3
        source = HarvestSourceFactory()
        backend = MockBackend(source)
        backend.mock_items = DatasetFactory.build_batch(
            nb_datasets, remote_id=True
        ) + DataserviceFactory.build_batch(nb_dataservices, remote_id=True)

        # create a dangling dataset to be archived
        last_update = datetime.now(UTC) - timedelta(days=grace_days + 1)
        dataset_arch = DatasetFactory(
            harvest={
                "domain": source.domain,
                "source_id": str(source.id),
                "remote_id": "dataset-not-on-remote",
                "last_update": last_update,
            }
        )
        dataservice_arch = DataserviceFactory(
            harvest={
                "domain": source.domain,
                "source_id": str(source.id),
                "remote_id": "dataservice-not-on-remote",
                "last_update": last_update,
            }
        )

        # create a dangling dataset that _won't_ be archived because of grace period
        last_update = datetime.now(UTC) - timedelta(days=grace_days - 1)
        dataset_no_arch = DatasetFactory(
            harvest={
                "domain": source.domain,
                "source_id": str(source.id),
                "remote_id": "dataset-not-on-remote-two",
                "last_update": last_update,
            }
        )
        dataservice_no_arch = DataserviceFactory(
            harvest={
                "domain": source.domain,
                "source_id": str(source.id),
                "remote_id": "dataservice-not-on-remote-two",
                "last_update": last_update,
            }
        )

        job = backend.harvest()

        # all items except *_arch: 3 mocks + 1 manual (*_no_arch)
        assert len(job.items) == (nb_datasets + 1) + (nb_dataservices + 1)
        # all items: 3 mocks + 2 manuals (*_arch and *_no_arch)
        assert Dataset.objects.count() == nb_datasets + 2
        assert Dataservice.objects.count() == nb_dataservices + 2

        archived_items = [i for i in job.items if i.status == "archived"]
        assert len(archived_items) == 2
        assert archived_items[0].dataset == dataset_arch
        assert archived_items[0].dataservice is None
        assert archived_items[1].dataset is None
        assert archived_items[1].dataservice == dataservice_arch

        dataset_arch.reload()
        assert dataset_arch.archived is not None
        assert "archived_at" in dataset_arch.harvest
        assert "archived_reason" in dataset_arch.harvest

        dataset_no_arch.reload()
        assert dataset_no_arch.archived is None
        assert "archived_at" not in dataset_no_arch.harvest
        assert "archived_reason" not in dataset_no_arch.harvest

        dataservice_arch.reload()
        assert dataservice_arch.archived_at is not None
        assert "archived_at" in dataservice_arch.harvest
        assert "archived_reason" in dataservice_arch.harvest

        dataservice_no_arch.reload()
        assert dataservice_no_arch.archived_at is None
        assert "archived_at" not in dataservice_no_arch.harvest
        assert "archived_reason" not in dataservice_no_arch.harvest

        # FIXME: backend.mock_items[i].remote_id

        # test unarchive: archive manually then relaunch harvest
        dataset = Dataset.objects.get(**{"harvest__remote_id": backend.mock_items[0].remote_id})
        dataset.archived = datetime.now(UTC)
        dataset.harvest.archived_at = datetime.now(UTC)
        dataset.harvest.archived_reason = "not-on-remote"
        dataset.save()

        dataservice = Dataservice.objects.get(
            **{"harvest__remote_id": backend.mock_items[nb_datasets].remote_id}
        )
        dataservice.archived_at = datetime.now(UTC)
        dataservice.harvest.archived_at = datetime.now(UTC)
        dataservice.harvest.archived_reason = "not-on-remote"
        dataservice.save()

        backend.harvest()

        dataset.reload()
        assert dataset.archived is None
        assert "archived_at" not in dataset.harvest
        assert "archived_reason" not in dataset.harvest

        dataservice.reload()
        assert dataservice.archived_at is None
        assert "archived_at" not in dataservice.harvest
        assert "archived_reason" not in dataservice.harvest

    def test_harvest_datasets_get_deleted(self):
        backend = MockBackend(HarvestSourceFactory())
        backend.mock_items = DatasetFactory.build_batch(3, remote_id=True)

        job = backend.harvest()

        for item in job.items:
            assert item.dataset is not None
        for dataset in Dataset.objects():
            dataset.deleted = "2016-01-01"
            dataset.save()

        tasks.purge_datasets()
        job.reload()
        for item in job.items:
            assert item.dataset is None

    def test_no_datasets_duplication(self):
        duplicated_remote_id_uri = "http://example.com/duplicated_remote_id_uri"
        nb_datasets = 3
        source = HarvestSourceFactory()
        backend = MockBackend(source)
        backend.mock_items = DatasetFactory.build_batch(
            nb_datasets, remote_id=True
        ) + DatasetFactory.build_batch(1, remote_id=duplicated_remote_id_uri)

        # FIXME: backend.mock_items[0].remote_id

        # Create a dataset that should be reused by the harvest, which will update it
        # instead of creating a new one, as it has the same remote_id, domain and source_id.
        dataset_reused = DatasetFactory(
            title="Reused Dataset",
            harvest={
                "domain": source.domain,
                "remote_id": backend.mock_items[
                    0
                ].remote_id,  # the MockBackend harvest should reuse this dataset
                "source_id": str(source.id),
            },
        )
        # Create a dataset that should be reused even though it's a different `source_id` and `domain,
        # because the remote_id is the same and an URI.
        dataset_reused_uri = DatasetFactory(
            title="Reused Dataset with URI",
            harvest={
                "domain": "some-other-domain",
                # the MockBackend harvest above should reuse this dataset with the same remote_id URI
                "remote_id": duplicated_remote_id_uri,
                "source_id": "some-other-source-id",
            },
        )
        # Create a dataset that should not be reused even though it's the same `remote_id`,
        # as it's not an URI, and has a different domain and source id.
        dataset_not_reused = DatasetFactory(
            title="Duplicated Dataset",
            harvest={
                "domain": "some-other-domain",
                "remote_id": backend.mock_items[
                    0
                ].remote_id,  # the "source" harvest above should create another dataset with the same remote_id
                "source_id": "some-other-source-id",
            },
        )

        job = backend.harvest()

        # 3 (nb_datasets) + 1 (dataset_remote_ids) created by the HarvestSourceFactory
        assert len(job.items) == nb_datasets + 1
        # all datasets : 4 mocks (3 nb_datasets + 1 dataset_remote_ids) + 3 created with DatasetFactory - 2 reused
        assert Dataset.objects.count() == nb_datasets + 1 + 3 - 2
        assert (
            # and not 3, data_reused was not duplicated
            Dataset.objects(harvest__remote_id=backend.mock_items[0].remote_id).count() == 2
        )
        # The dataset not reused wasn't overwritten nor updated by the harvest.
        dataset_not_reused.reload()
        assert dataset_not_reused.harvest.domain == "some-other-domain"
        assert dataset_not_reused.harvest.source_id == "some-other-source-id"
        # The "reused dataset" was overwritten and updated by the harvest.
        dataset_reused.reload()
        # The "reused dataset with uri" was overwritten and updated by the harvest.
        dataset_reused_uri.reload()
        assert dataset_reused_uri.harvest.domain == source.domain
        assert dataset_reused_uri.harvest.source_id == str(source.id)

    def test_duplicate_remote_ids(self):
        dataset_records = [
            DatasetFactory.build(remote_id="dataset-1"),
            DatasetFactory.build(remote_id="dataset-2"),
            DatasetFactory.build(remote_id="dataset-3"),
            DatasetFactory.build(remote_id="dataset-3"),
            DatasetFactory.build(remote_id="dataset-1"),
        ]
        dataservice_records = [
            DataserviceFactory.build(remote_id="dataservice-1"),
            DataserviceFactory.build(remote_id="dataservice-2"),
            DataserviceFactory.build(remote_id="dataservice-2"),
        ]
        backend = MockBackend(HarvestSourceFactory())
        backend.mock_items = dataset_records + dataservice_records

        job = backend.harvest()

        assert job.status == "done-errors"
        assert len(job.items) == len(dataset_records) + len(dataservice_records)
        assert Dataset.objects.count() == len({d.remote_id for d in dataset_records})
        assert Dataservice.objects.count() == len({d.remote_id for d in dataservice_records})
        seen = set()
        for job in job.items:
            if job.remote_id not in seen:
                assert job.status == "done"
                seen.add(job.remote_id)
            else:
                assert job.status == "failed"
                assert job.remote_id in job.errors[0].message

    @pytest.mark.options(CDATA_BASE_URL="http://localhost")
    @pytest.mark.parametrize(
        "owner_param, owner_factory",
        [("organization", OrganizationFactory), ("owner", UserFactory)],
    )
    def test_unique_ownership_same_uri_remote_id(self, owner_param, owner_factory):
        backend1 = MockBackend(
            HarvestSourceFactory(
                url="https://data.example.com/catalog",
                **{owner_param: owner_factory()},
            )
        )
        backend1.mock_items = [
            DatasetFactory.build(remote_id="https://data.example.com/catalog/dataset-repeat"),
            DatasetFactory.build(remote_id="https://data.example.com/catalog/dataset-unique"),
            # dataservices don't check on uri remote_id (bug?)  # FIXME
        ]

        job1 = backend1.harvest()

        assert job1.status == "done"
        assert len(job1.items) == 2

        backend2 = MockBackend(
            HarvestSourceFactory(
                url="https://other.example.com/catalog",
                **{owner_param: owner_factory()},
            )
        )
        backend2.mock_items = [
            DatasetFactory.build(remote_id="https://data.example.com/catalog/dataset-repeat"),
            DatasetFactory.build(remote_id="https://other.example.com/catalog/dataset-unique"),
        ]

        job2 = backend2.harvest()

        assert job2.status == "done-errors"
        assert len(job2.items) == 2
        for item in job2.items:
            if not item.remote_id.endswith("-repeat"):
                assert item.status == "done"
            else:
                assert item.status == "failed"
                assert getattr(backend1.source, owner_param).page() in item.errors[0].message

    @pytest.mark.options(CDATA_BASE_URL="http://localhost")
    @pytest.mark.parametrize(
        "owner_param, owner_factory",
        [("organization", OrganizationFactory), ("owner", UserFactory)],
    )
    def test_unique_ownership_same_domain(self, owner_param, owner_factory):
        backend1 = MockBackend(
            HarvestSourceFactory(
                url="https://data.example.com/catalog",
                **{owner_param: owner_factory()},
            )
        )
        backend1.mock_items = [
            DatasetFactory.build(remote_id="dataset-repeat"),
            DatasetFactory.build(remote_id="dataset-unique-1"),
            DataserviceFactory.build(remote_id="dataservice-repeat"),
            DataserviceFactory.build(remote_id="dataservice-unique-1"),
        ]

        job1 = backend1.harvest()

        assert job1.status == "done"
        assert len(job1.items) == 4

        backend2 = MockBackend(
            HarvestSourceFactory(
                url="https://data.example.com/other-catalog",  # same domain as backend1
                **{owner_param: owner_factory()},
            )
        )
        backend2.mock_items = [
            DatasetFactory.build(remote_id="dataset-repeat"),
            DatasetFactory.build(remote_id="dataset-unique-2"),
            DataserviceFactory.build(remote_id="dataservice-repeat"),
            DataserviceFactory.build(remote_id="dataservice-unique-2"),
        ]

        job2 = backend2.harvest()

        assert job2.status == "done-errors"
        assert len(job2.items) == 4
        for item in job2.items:
            if not item.remote_id.endswith("-repeat"):
                assert item.status == "done"
            else:
                assert item.status == "failed"
                assert getattr(backend1.source, owner_param).page() in item.errors[0].message

    @pytest.mark.parametrize(
        "error, job_status",
        argvalues(
            (None, "done"),
            (MockHarvestError(HarvestValidationError("harvest-validation-error")), "failed"),
            (
                MockHarvestError(requests.exceptions.ConnectionError("harvest-connection-error")),
                "failed",
            ),
            (MockHarvestError(requests.exceptions.Timeout("harvest-timeout-error")), "failed"),
            (MockHarvestError(Exception("harvest-generic-error")), "failed"),
            (MockRecordError(HarvestSkipException("record-skip-error")), "done"),
            (MockRecordError(HarvestValidationError("record-validation-error")), "done-errors"),
            (MockRecordError(Exception("record-generic-error")), "done-errors"),
            ids=lambda t: str(t[0].exception) if t[0] else "success",
        ),
    )
    @pytest.mark.parametrize("dryrun", [False, True], ids=["liverun", "dryrun"])
    def test_harvest_loop(self, error, job_status, dryrun, mocker: MockerFixture):
        liverun = not dryrun

        nb_datasets = 3
        nb_dataservices = 2
        record_errors = [error] if isinstance(error, MockRecordError) else []
        harvest_errors = (
            [error, DatasetFactory.build(remote_id="never-processed")]
            if isinstance(error, MockHarvestError)
            else []
        )

        org = OrganizationFactory()
        backend = MockBackend(HarvestSourceFactory(organization=org), dryrun=dryrun)
        backend.mock_items = [
            *record_errors,  # at the beginning to check processing continues
            *DatasetFactory.build_batch(nb_datasets, remote_id=True),
            *DataserviceFactory.build_batch(nb_dataservices, remote_id=True),
            *harvest_errors,  # at the end to check *.objects.count() > 0
        ]

        signals = {
            signal: signal.connect(mocker.Mock(name=signal.name), weak=False)
            for signal in [before_harvest_job, after_harvest_job, pre_save]
        }

        try:
            job = backend.harvest()

            assert job.status == job_status

            approx_date = pytest.approx(datetime.now(UTC), abs=timedelta(seconds=1))
            assert job.started == approx_date
            assert job.ended == approx_date
            assert job.started < job.ended

            assert len(job.items) == nb_datasets + nb_dataservices + len(record_errors)

            assert len(job.errors) == (1 if harvest_errors else 0)
            if harvest_errors:
                assert job.errors[0].message == str(error.exception)

            # mongo objects
            assert Dataset.objects.count() == (nb_datasets if liverun else 0)
            assert Dataservice.objects.count() == (nb_dataservices if liverun else 0)

            # gated metrics (behind Organization.compute_aggregate_metrics)
            for metric in ["datasets_by_months", "dataservices_by_months"]:
                assert (metric in org.metrics) is (True if liverun else False)

            # signals
            signals[before_harvest_job].assert_called_with(backend)
            signals[after_harvest_job].assert_called_with(backend)
            if liverun:
                signals[pre_save].assert_called_with(HarvestJob, document=job)
            else:
                signals[pre_save].assert_not_called()
        finally:
            for signal, receiver in signals.items():
                signal.disconnect(receiver)

    @pytest.mark.parametrize("max_items", [2, 3, 4, 6, 7])
    def test_harvest_max_items(self, max_items):
        n = 3
        # max_items == 2 * n will log an error in the current implementation,
        # so we include the case in max_reached
        max_reached = max_items <= 2 * n
        backend = MockBackend(HarvestSourceFactory(), max_items=max_items)
        backend.mock_items = DatasetFactory.build_batch(
            n, remote_id=True
        ) + DataserviceFactory.build_batch(n, remote_id=True)

        job = backend.harvest()

        assert job.status == "done"
        assert len(job.items) == min(2 * n, max_items)
        assert len(job.errors) == (1 if max_reached else 0)
        if max_reached:
            assert job.errors[0].message.startswith(f"{max_items} max items reached")
        assert Dataset.objects.count() == min(n, max_items)
        assert Dataservice.objects.count() == max(min(n, max_items - n), 0)

    def test_harvest_max_items_preview(self):
        backend = MockBackend(HarvestSourceFactory(), max_items=2, dryrun=True)
        backend.mock_items = DatasetFactory.build_batch(3) + DataserviceFactory.build_batch(3)

        job = backend.harvest()

        assert job.status == "done"
        assert len(job.items) == 2
        # we don't log the max_items error in dryrun
        assert len(job.errors) == 0

    @pytest.mark.parametrize(
        "exception_class",
        [HarvestSkipException, HarvestValidationError, Exception],
    )
    def test_harvest_max_items_with_failure(self, exception_class):
        backend = MockBackend(HarvestSourceFactory(), max_items=2)
        backend.mock_items = [
            DatasetFactory.build(remote_id="dataset-ok"),
            MockRecordError(exception_class()),
            DatasetFactory.build(remote_id="dataset-ignored"),  # not processed
        ]

        job = backend.harvest()

        assert len(job.items) == 2
        assert len(job.errors) == 1
        assert Dataset.objects.count() == 1

    @pytest.mark.parametrize(
        "record, item_status",
        argvalues(
            (DatasetFactory.build(remote_id="dataset"), "done"),
            (DataserviceFactory.build(remote_id="dataservice"), "done"),
            (DatasetFactory.build(remote_id=None), "skipped"),
            (MockRecordError(HarvestSkipException("skip-error")), "skipped"),
            (MockRecordError(HarvestValidationError("validation-error")), "failed"),
            (MockRecordError(Exception("generic-error")), "failed"),
            ids=lambda t: getattr(t[0], "remote_id", "missing-id"),
        ),
    )
    @pytest.mark.parametrize("dryrun", [False, True], ids=["liverun", "dryrun"])
    def test_process_item(self, record, item_status, dryrun, mocker: MockerFixture):
        liverun = not dryrun
        record_error = item_status != "done"

        org = OrganizationFactory()
        backend = MockBackend(HarvestSourceFactory(organization=org), dryrun=dryrun)
        backend.job = HarvestJob()
        backend.remote_ids = set()

        signals = {
            signal: signal.connect(mocker.Mock(name=signal.name), weak=False)
            for signal in [pre_save]
        }

        try:
            remote_id = getattr(record, "remote_id", None)
            backend.process_item(remote_id, backend.item_processor, record)

            assert len(backend.job.items) == 1
            harvest_item = backend.job.items[0]
            assert isinstance(harvest_item, HarvestItem)

            assert harvest_item.remote_id == remote_id
            assert harvest_item.status == item_status

            approx_date = pytest.approx(datetime.now(UTC), abs=timedelta(seconds=1))
            assert harvest_item.started == approx_date
            assert harvest_item.ended == approx_date
            assert harvest_item.started < harvest_item.ended

            assert len(harvest_item.errors) == (1 if record_error else 0)
            if record_error:
                assert harvest_item.errors[0].message == (
                    "missing identifier"
                    if not hasattr(record, "remote_id")
                    else str(record.exception)
                )

            # nothing more to test for error cases
            if record_error:
                return

            assert harvest_item.remote_url.endswith(remote_id)

            # harvested item
            item_type = type(record)
            if item_type is Dataset:
                item = harvest_item.dataset
            elif item_type is Dataservice:
                item = harvest_item.dataservice
            else:
                assert False, "inconsistent test"

            assert isinstance(item, item_type)
            assert item.pk is not None
            assert item.archived_at is None
            assert item.harvest is not None  # further tested in test_update_harvest_metadata

            # mongo objects
            assert item_type.objects.count() == (1 if liverun else 0)

            # gated metrics
            assert org.compute_aggregate_metrics is False
            assert org in backend.organizations_to_update

            # signals
            if liverun:
                signals[pre_save].assert_any_call(item_type, document=item)
                signals[pre_save].assert_any_call(HarvestJob, document=backend.job)
            else:
                signals[pre_save].assert_not_called()
        finally:
            for signal, receiver in signals.items():
                signal.disconnect(receiver)

    def test_process_item_archived(self):
        backend = MockBackend(HarvestSourceFactory())
        backend.job = HarvestJob()
        backend.remote_ids = set()

        dataset = DatasetFactory(
            archived=datetime.now(UTC),
            harvest={
                "source_id": str(backend.source.id),
                "remote_id": "archived-dataset",
                "archived_at": datetime.now(UTC),
                "archived_reason": "not-on-remote",
            },
        )
        assert dataset.archived_at is not None

        backend.process_item(dataset.harvest.remote_id, backend.item_processor, dataset)

        item = backend.job.items[0].dataset
        assert item == dataset
        assert item.archived_at is None

    @pytest.mark.parametrize(
        "owner_field, owner_factory",
        argvalues(
            [
                (None, None),
                ("organization", OrganizationFactory),
                ("owner", UserFactory),
            ],
            ids=lambda t: str(t[0]),
        ),
    )
    def test_get_item_new(self, owner_field, owner_factory):
        owner = owner_factory() if owner_field else None
        backend = MockBackend(HarvestSourceFactory(**({owner_field: owner} if owner else {})))

        item = backend.get_item("new", Dataset)
        assert isinstance(item, Dataset)
        assert item.id is None  # newly instantiated item (not saved => no mongo-generated id)
        if owner:
            assert getattr(item, owner_field) is owner
        assert item.harvest is not None

    @pytest.mark.parametrize(
        "match_field, match_value",
        argvalues(
            [
                ("domain", lambda s: s.domain),
                ("source_id", lambda s: str(s.id)),
            ],
            ids=lambda t: str(t[0]),
        ),
    )
    def test_get_item_existing(self, match_field, match_value):
        source = HarvestSourceFactory()
        last_update = datetime(2026, 1, 1)
        dataset = DatasetFactory(
            harvest={
                "remote_id": "dataset",
                "last_update": last_update,
                **{match_field: match_value(source)},
            }
        )
        backend = MockBackend(source)

        # same source/domain + correct type => existing item
        item = backend.get_item(dataset.harvest.remote_id, Dataset)
        assert isinstance(item, Dataset)
        assert item.id == dataset.id
        # get_item shouldn't override harvest info
        assert item.harvest.last_update == last_update

        # same source/domain + wrong type => new item
        item = backend.get_item(dataset.harvest.remote_id, Dataservice)
        assert item.id is None  # newly instantiated dataservice

        # different source/domain => new item
        backend2 = MockBackend(HarvestSourceFactory())
        item = backend2.get_item(dataset.harvest.remote_id, Dataset)
        assert item.id is None  # newly instantiated dataset

    def test_update_harvest_metadata(self):
        source = HarvestSourceFactory()
        backend = MockBackend(source)

        metadata = HarvestMetadata()
        m = backend.update_harvest_metadata(metadata, "test")

        assert m is metadata
        assert m.backend == backend.display_name
        assert m.domain == source.domain
        assert m.source_id == str(source.id)
        assert m.source_url == source.url
        assert m.remote_id == "test"
        assert m.remote_url is None  # not set by update_harvest_metadata()
        assert m.created_at is None  # not set by update_harvest_metadata()
        assert m.modified_at is None  # not set by update_harvest_metadata()
        assert m.last_update == pytest.approx(datetime.now(UTC), abs=timedelta(seconds=1))
        assert m.archived_at is None  # set but None
        assert m.archived_reason is None  # set but None


# class HarvestItemLogsTest(PytestOnlyDBTestCase):
#     @pytest.mark.parametrize("config_key", ["dataset_remote_ids", "dataservice_remote_ids"])
#     def test_logs_emitted_while_processing_are_reported_on_the_item(self, config_key):
#         backend = LoggingItemBackend(HarvestSourceFactory(config={config_key: ["fake-1"]}))

#         job = backend.harvest()

#         assert job.items[0].status == "done"
#         assert ITEM_LOG_MESSAGE in [entry.message for entry in job.items[0].logs]


# class HarvestErrorReportingTest(PytestOnlyDBTestCase):
#     """A failing remote belongs to the harvest report; only udata bugs go to Sentry."""

#     @pytest.mark.parametrize(
#         "exception",
#         argvalues(
#             (requests.exceptions.ConnectTimeout("Connection timed out"), "timeout"),
#             (
#                 requests.exceptions.ConnectionError(
#                     "Failed to resolve 'example.com' (Name resolution failed)"
#                 ),
#                 "resolution",
#             ),
#             (requests.exceptions.SSLError("SSL: CERTIFICATE_VERIFY_FAILED"), "certificate"),
#         ),
#     )
#     def test_job_connection_error_is_not_sent_to_sentry(self, rmock, harvest_logs, exception):
#         url = "https://remote.example.com/catalog"
#         rmock.get(url, exc=exception)
#         source = HarvestSourceFactory(url=url)

#         job = MockFetchingBackend(source).harvest()

#         assert job.status == "failed"
#         assert len(job.errors) == 1
#         assert str(exception) in job.errors[0].message
#         harvest_logs.warning.assert_called_once()
#         assert "request error" in harvest_logs.warning.call_args[0][0].lower()
#         harvest_logs.assert_not_sent_to_sentry()

#     @pytest.mark.parametrize("status_code", [404, 502])
#     def test_job_http_error_is_not_sent_to_sentry(self, rmock, harvest_logs, status_code):
#         url = "https://remote.example.com/catalog"
#         rmock.get(url, status_code=status_code)
#         source = HarvestSourceFactory(url=url)

#         job = MockFetchingBackend(source).harvest()

#         assert job.status == "failed"
#         assert str(status_code) in job.errors[0].message
#         harvest_logs.warning.assert_called_once()
#         harvest_logs.assert_not_sent_to_sentry()

#     def test_job_redirect_is_not_sent_to_sentry(self, rmock, harvest_logs):
#         url = "https://remote.example.com/catalog"
#         rmock.get(url, status_code=302, headers={"Location": "https://elsewhere.example.com/"})
#         source = HarvestSourceFactory(url=url)

#         job = MockFetchingBackend(source).harvest()

#         assert job.status == "failed"
#         assert "Redirect (302) not allowed" in job.errors[0].message
#         harvest_logs.warning.assert_called_once()
#         harvest_logs.assert_not_sent_to_sentry()

#     def test_job_validation_error_is_not_sent_to_sentry(self, harvest_logs):
#         backend = FailingBackend(HarvestSourceFactory())
#         backend.exception = HarvestValidationError("Descriptor declares a DTD")

#         job = backend.harvest()

#         assert job.status == "failed"
#         assert "DTD" in job.errors[0].message
#         harvest_logs.warning.assert_called_once()
#         harvest_logs.assert_not_sent_to_sentry()

#     def test_job_unexpected_error_is_sent_to_sentry(self, harvest_logs):
#         backend = FailingBackend(HarvestSourceFactory())
#         backend.exception = AttributeError("'NoneType' object has no attribute 'title'")

#         job = backend.harvest()

#         assert job.status == "failed"
#         assert "'NoneType' object has no attribute 'title'" in job.errors[0].message
#         harvest_logs.assert_sent_to_sentry()

#     @pytest.mark.parametrize("config_key", ["dataset_remote_ids", "dataservice_remote_ids"])
#     def test_item_http_error_is_not_sent_to_sentry(self, harvest_logs, config_key):
#         backend = FailingItemBackend(HarvestSourceFactory(config={config_key: ["fake-1"]}))
#         backend.exception = requests.exceptions.HTTPError(
#             "403 Client Error: Forbidden for url: https://remote.example.com/package_show"
#         )

#         job = backend.harvest()

#         assert job.items[0].status == "failed"
#         assert "403 Client Error" in job.items[0].errors[0].message
#         # The message names the failure, only the traceback names the failing call.
#         assert "inner_process_" in job.items[0].errors[0].details
#         harvest_logs.warning.assert_called_once()
#         harvest_logs.assert_not_sent_to_sentry()

#     @pytest.mark.parametrize("config_key", ["dataset_remote_ids", "dataservice_remote_ids"])
#     def test_item_validation_error_is_not_sent_to_sentry(self, harvest_logs, config_key):
#         backend = FailingItemBackend(HarvestSourceFactory(config={config_key: ["fake-1"]}))
#         backend.exception = MongoValidationError("URL invalide", field_name="resources")

#         job = backend.harvest()

#         assert job.items[0].status == "failed"
#         assert "URL invalide" in job.items[0].errors[0].message
#         harvest_logs.info.assert_called_once()
#         harvest_logs.assert_not_sent_to_sentry()

#     @pytest.mark.parametrize("config_key", ["dataset_remote_ids", "dataservice_remote_ids"])
#     def test_item_unexpected_error_is_sent_to_sentry(self, harvest_logs, config_key):
#         backend = FailingItemBackend(HarvestSourceFactory(config={config_key: ["fake-1"]}))
#         backend.exception = AttributeError("'NoneType' object has no attribute 'title'")

#         job = backend.harvest()

#         assert job.items[0].status == "failed"
#         assert "'NoneType' object has no attribute 'title'" in job.items[0].errors[0].message
#         harvest_logs.assert_sent_to_sentry()

#     def test_invalid_remote_resource_url_only_fails_its_item(self, harvest_logs):
#         backend = InvalidResourceBackend(
#             HarvestSourceFactory(config={"dataset_remote_ids": ["fake-1", "fake-2"]})
#         )

#         job = backend.harvest()

#         assert job.status == "done-errors"
#         assert [item.status for item in job.items] == ["failed", "failed"]
#         assert "resources" in job.items[0].errors[0].message
#         harvest_logs.assert_not_sent_to_sentry()


class BaseBackendValidateTest(PytestOnlyDBTestCase):
    @pytest.fixture
    def validate(self):
        return MockBackend(HarvestSourceFactory()).validate

    def test_valid_data(self, validate):
        schema = Schema({"key": str})
        data = {"key": "value"}
        assert validate(data, schema) == data

    def test_handle_basic_error(self, validate):
        schema = Schema({"bad-value": str})
        data = {"bad-value": 42}
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert "[bad-value] expected str: 42" in msg

    def test_handle_required_values(self, validate):
        schema = Schema({"missing": str}, required=True)
        data = {}
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert "[missing] required key not provided" in msg
        assert "[missing] required key not provided: None" not in msg

    def test_handle_multiple_errors_on_object(self, validate):
        schema = Schema({"bad-value": str, "other-bad-value": int})
        data = {"bad-value": 42, "other-bad-value": "wrong"}
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert "[bad-value] expected str: 42" in msg
        assert "[other-bad-value] expected int: wrong" in msg

    def test_handle_multiple_error_on_nested_object(self, validate):
        schema = Schema({"nested": {"bad-value": str, "other-bad-value": int}})
        data = {"nested": {"bad-value": 42, "other-bad-value": "wrong"}}
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert "[nested.bad-value] expected str: 42" in msg
        assert "[nested.other-bad-value] expected int: wrong" in msg

    def test_handle_multiple_error_on_nested_list(self, validate):
        schema = Schema({"nested": [{"bad-value": str, "other-bad-value": int}]})
        data = {
            "nested": [
                {"bad-value": 42, "other-bad-value": "wrong"},
            ]
        }
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert "[nested.0.bad-value] expected str: 42" in msg
        assert "[nested.0.other-bad-value] expected int: wrong" in msg

    # See: https://github.com/alecthomas/voluptuous/pull/330
    @pytest.mark.skip(reason="Not yet supported by Voluptuous")
    def test_handle_multiple_error_on_nested_list_items(self, validate):
        schema = Schema({"nested": [{"bad-value": str, "other-bad-value": int}]})
        data = {
            "nested": [
                {"bad-value": 42, "other-bad-value": "wrong"},
                {"bad-value": 43, "other-bad-value": "bad"},
            ]
        }
        with pytest.raises(HarvestException) as excinfo:
            validate(data, schema)
        msg = str(excinfo.value)
        assert "[nested.0.bad-value] expected str: 42" in msg
        assert "[nested.0.other-bad-value] expected int: wrong" in msg
        assert "[nested.1.bad-value] expected str: 43" in msg
        assert "[nested.1.other-bad-value] expected int: bad" in msg


class AllBackendsTest:
    def test_all_backends_have_unique_display_name(self):
        """Ensure all harvest backends have unique display_name values."""
        backends = get_all_backends()

        display_names = {}
        for name, backend in backends.items():
            display_name = backend.display_name
            assert display_name is not None, f"Backend '{name}' has no display_name"
            assert display_name not in display_names, (
                f"Duplicate display_name '{display_name}' found in backends "
                f"'{display_names[display_name]}' and '{name}'"
            )
            display_names[display_name] = name
