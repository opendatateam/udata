from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Generic, Never, Self, TypeVar
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
from udata.harvest.exceptions import HarvestSkipException, HarvestValidationError
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
from ..exceptions import HarvestException
from .factories import HarvestSourceFactory


class Unknown:
    pass


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
        self.mock_items: Sequence["MockItem"] = []
        self.mock_last_modified: datetime | None = None

    @override
    def inner_harvest(self):
        for item in self.mock_items:
            item.process(self)


class MockFetchingBackend(MockBackend):
    """A backend that really goes over the network, to exercise the HTTP layer."""

    name = "mock-fetching-backend"

    def inner_harvest(self):
        self.get(self.source.url)


@dataclass(frozen=True)
class MockItem(ABC):
    identifier: str | None

    @abstractmethod
    def process(self, backend: MockBackend): ...


@dataclass(frozen=True)
class MockHarvestError(MockItem):
    exception: type[Exception]

    def process(self, backend: MockBackend) -> Never:
        raise self.exception(f"mock harvest error for {self.identifier}")


H = TypeVar("H", bound=Harvestable)


@dataclass(frozen=True)
class MockRecord(MockItem, Generic[H]):
    @classmethod
    def create(cls, num: int) -> list[Self]:
        return [cls(f"{cls.__name__.removeprefix('Mock').lower()}-{i}") for i in range(num)]

    @abstractmethod
    def item_processor(self, harvest_item: HarvestItem, backend: MockBackend) -> H: ...

    def process(self, backend: MockBackend):
        backend.process_item(self.identifier, self.item_processor, backend)

    def mock_item(self, item: H, fields: dict):
        for key, value in fields.items():
            if getattr(item, key) is None:
                setattr(item, key, value)
        item.harvest.remote_url = f"http://www.example.com/records/{self.identifier}"


@dataclass(frozen=True)
class MockDataset(MockRecord[Dataset]):
    def item_processor(self, harvest_item: HarvestItem, backend: MockBackend) -> Dataset:
        item = backend.get_item(harvest_item.remote_id, Dataset)
        self.mock_item(item, DatasetFactory.as_dict(visible=True))
        if backend.mock_last_modified:
            item.last_modified_internal = backend.mock_last_modified
        return item


@dataclass(frozen=True)
class MockDataservice(MockRecord[Dataservice]):
    def item_processor(self, harvest_item: HarvestItem, backend: MockBackend) -> Dataservice:
        item = backend.get_item(harvest_item.remote_id, Dataservice)
        self.mock_item(item, DataserviceFactory.as_dict())
        return item


@dataclass(frozen=True)
class MockRecordError(MockRecord):
    exception: type[Exception]

    def item_processor(self, harvest_item: HarvestItem, backend: MockBackend) -> Never:
        raise self.exception(f"mock record error for {self.identifier}")


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
        backend.mock_items = MockDataset.create(nb_datasets)

        before = datetime.now(UTC)
        job = backend.harvest()
        after = datetime.now(UTC)

        assert len(job.items) == nb_datasets
        assert Dataset.objects.count() == nb_datasets
        before_naive = before.replace(tzinfo=None)
        after_naive = after.replace(tzinfo=None)
        for dataset in Dataset.objects():
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
            assert dataset.harvest.source_id == str(source.id)
            assert dataset.harvest.domain == source.domain
            assert dataset.harvest.remote_id.startswith("dataset-")
            assert before_naive <= last_update_naive <= after_naive

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
        backend.mock_items = MockDataset.create(n) + MockDataservice.create(n)

        job = backend.harvest()

        assert len(job.items) == 2 * n
        assert all([item.remote_url for item in job.items])

    def test_harvest_source_id(self):
        nb_datasets = 3
        source = HarvestSourceFactory()
        backend = MockBackend(source)
        backend.mock_items = MockDataset.create(nb_datasets)

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
        backend.mock_items = MockDataset.create(1)
        backend.mock_last_modified = last_modified

        backend.harvest()
        dataset = Dataset.objects.first()
        assert_equal_dates(dataset.last_modified_internal, last_modified)
        assert_equal_dates(dataset.harvest.last_update, datetime.now(UTC))

    def test_dont_overwrite_last_modified_even_if_set_to_same(self):
        last_modified = faker.date_time_between(start_date="-30y", end_date="-1y")
        backend = MockBackend(HarvestSourceFactory())
        backend.mock_items = MockDataset.create(1)
        backend.mock_last_modified = last_modified

        backend.harvest()
        backend.harvest()  # Harvest twice to test same last_modified
        dataset = Dataset.objects.first()
        assert_equal_dates(dataset.last_modified_internal, last_modified)
        assert_equal_dates(dataset.harvest.last_update, datetime.now(UTC))

    def test_autoarchive(self, app):
        nb_datasets = 3
        nb_dataservices = 3
        source = HarvestSourceFactory()
        backend = MockBackend(source)
        backend.mock_items = MockDataset.create(nb_datasets) + MockDataservice.create(
            nb_dataservices
        )

        # create a dangling dataset to be archived
        limit = app.config["HARVEST_AUTOARCHIVE_GRACE_DAYS"]
        last_update = datetime.now(UTC) - timedelta(days=limit + 1)
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
        limit = app.config["HARVEST_AUTOARCHIVE_GRACE_DAYS"]
        last_update = datetime.now(UTC) - timedelta(days=limit - 1)
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

        # all datasets except arch : 3 mocks + 1 manual (no_arch)
        assert len(job.items) == (nb_datasets + 1) + (nb_dataservices + 1)
        # all datasets : 3 mocks + 2 manuals (arch and no_arch)
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

        # test unarchive: archive manually then relaunch harvest
        dataset = Dataset.objects.get(**{"harvest__remote_id": "dataset-1"})
        dataset.archived = datetime.now(UTC)
        dataset.harvest.archived_at = datetime.now(UTC)
        dataset.harvest.archived_reason = "not-on-remote"
        dataset.save()

        dataservice = Dataservice.objects.get(**{"harvest__remote_id": "dataservice-1"})
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
        backend.mock_items = MockDataset.create(3)

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

    def test_no_datasets_duplication(self, app):
        duplicated_remote_id_uri = "http://example.com/duplicated_remote_id_uri"
        nb_datasets = 3
        source = HarvestSourceFactory()
        backend = MockBackend(source)
        backend.mock_items = MockDataset.create(nb_datasets) + [
            MockDataset(duplicated_remote_id_uri)
        ]

        # Create a dataset that should be reused by the harvest, which will update it
        # instead of creating a new one, as it has the same remote_id, domain and source_id.
        dataset_reused = DatasetFactory(
            title="Reused Dataset",
            harvest={
                "domain": source.domain,
                "remote_id": "dataset-0",  # the MockBackend harvest should reuse this dataset
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
                "remote_id": "dataset-0",  # the "source" harvest above should create another dataset with the same remote_id
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
            Dataset.objects(harvest__remote_id="dataset-0").count() == 2
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
            MockDataset("dataset-1"),
            MockDataset("dataset-2"),
            MockDataset("dataset-3"),
            MockDataset("dataset-3"),
            MockDataset("dataset-1"),
        ]
        dataservice_records = [
            MockDataservice("dataservice-1"),
            MockDataservice("dataservice-2"),
            MockDataservice("dataservice-2"),
        ]
        backend = MockBackend(HarvestSourceFactory())
        backend.mock_items = dataset_records + dataservice_records

        job = backend.harvest()
        assert job.status == "done-errors"
        assert len(job.items) == len(dataset_records) + len(dataservice_records)
        assert Dataset.objects.count() == len(set(dataset_records))
        assert Dataservice.objects.count() == len(set(dataservice_records))
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
            MockDataset("https://data.example.com/catalog/dataset-repeat"),
            MockDataset("https://data.example.com/catalog/dataset-unique"),
            # dataservices don't check on uri remote_id (bug?)
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
            MockDataset("https://data.example.com/catalog/dataset-repeat"),
            MockDataset("https://other.example.com/catalog/dataset-unique"),
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
            MockDataset("dataset-repeat"),
            MockDataset("dataset-unique-1"),
            MockDataservice("dataservice-repeat"),
            MockDataservice("dataservice-unique-1"),
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
            MockDataset("dataset-repeat"),
            MockDataset("dataset-unique-2"),
            MockDataservice("dataservice-repeat"),
            MockDataservice("dataservice-unique-2"),
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
            (MockHarvestError("harvest-validation-error", HarvestValidationError), "failed"),
            (
                MockHarvestError("harvest-connection-error", requests.exceptions.ConnectionError),
                "failed",
            ),
            (MockHarvestError("harvest-timeout-error", requests.exceptions.Timeout), "failed"),
            (MockHarvestError("harvest-generic-error", Exception), "failed"),
            (MockRecordError("record-skip-error", HarvestSkipException), "done"),
            (MockRecordError("record-validation-error", HarvestValidationError), "done-errors"),
            (MockRecordError("record-generic-error", Exception), "done-errors"),
            ids=lambda t: t[0].identifier if t[0] else "success",
        ),
    )
    @pytest.mark.parametrize("dryrun", [False, True], ids=["liverun", "dryrun"])
    def test_harvest_loop(self, error, job_status, dryrun, mocker: MockerFixture):
        liverun = not dryrun

        nb_datasets = 3
        nb_dataservices = 2
        record_errors = [error] if isinstance(error, MockRecordError) else []
        harvest_errors = (
            [error, MockDataset("never-processed")] if isinstance(error, MockHarvestError) else []
        )

        org = OrganizationFactory()
        backend = MockBackend(HarvestSourceFactory(organization=org), dryrun=dryrun)
        backend.mock_items = [
            *record_errors,  # at the beginning to check processing continues
            *MockDataset.create(nb_datasets),
            *MockDataservice.create(nb_dataservices),
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
                assert job.errors[0].message == f"mock harvest error for {error.identifier}"

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

    @pytest.mark.parametrize("max_items", [2, 3, 4])
    def test_harvest_max_items(self, max_items):
        n = 3
        assert max_items <= 2 * n
        backend = MockBackend(HarvestSourceFactory(), max_items=max_items)
        backend.mock_items = MockDataset.create(n) + MockDataservice.create(n)

        job = backend.harvest()
        assert job.status == "done"
        assert len(job.items) == max_items
        assert len(job.errors) == 1
        assert job.errors[0].message.startswith(f"{max_items} max items reached")
        assert Dataset.objects.count() == min(n, max_items)
        assert Dataservice.objects.count() == max(min(n, max_items - n), 0)

    def test_harvest_max_items_preview(self):
        backend = MockBackend(HarvestSourceFactory(), max_items=2, dryrun=True)
        backend.mock_items = MockDataset.create(3) + MockDataservice.create(3)

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
            MockDataset("dataset-ok-1"),
            MockRecordError("dataset-ko", exception_class),
            MockDataset("dataset-ok-2"),  # not processed
        ]

        job = backend.harvest()
        assert len(job.items) == 2
        assert len(job.errors) == 1
        assert Dataset.objects.count() == 1

    @pytest.mark.parametrize(
        "record, item_status",
        argvalues(
            (MockDataset("dataset"), "done"),
            (MockDataservice("dataservice"), "done"),
            (MockDataset(None), "skipped"),
            (MockRecordError("skip-error", HarvestSkipException), "skipped"),
            (MockRecordError("validation-error", HarvestValidationError), "failed"),
            (MockRecordError("generic-error", Exception), "failed"),
            ids=lambda t: t[0].identifier or "missing-id",
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
            record.process(backend)  # calls backend.process_item()

            assert len(backend.job.items) == 1
            harvest_item = backend.job.items[0]
            assert isinstance(harvest_item, HarvestItem)

            assert harvest_item.remote_id == record.identifier
            assert harvest_item.status == item_status

            approx_date = pytest.approx(datetime.now(UTC), abs=timedelta(seconds=1))
            assert harvest_item.started == approx_date
            assert harvest_item.ended == approx_date
            assert harvest_item.started < harvest_item.ended

            assert len(harvest_item.errors) == (1 if record_error else 0)
            if record_error:
                assert harvest_item.errors[0].message == (
                    f"mock record error for {record.identifier}"
                    if record.identifier
                    else "missing identifier"
                )

            # nothing more to test for error cases
            if record_error:
                return

            assert harvest_item.remote_url.endswith(record.identifier)

            # harvested item
            if isinstance(record, MockDataset):
                item = harvest_item.dataset
                item_type = Dataset
            elif isinstance(record, MockDataservice):
                item = harvest_item.dataservice
                item_type = Dataservice
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
                signals[pre_save].assert_any_call(type(item), document=item)
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

        MockDataset(dataset.harvest.remote_id).process(backend)  # calls backend.process_item()

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
