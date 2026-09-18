from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from urllib.parse import urlparse

import pytest
import requests
from typing_extensions import override
from voluptuous import Schema

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataset import tasks
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.harvest.exceptions import HarvestSkipException, HarvestValidationError
from udata.harvest.models import Harvestable, HarvestItem
from udata.ssrf import BlockedAddressError
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.helpers import assert_equal_dates
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


@dataclass(frozen=True)
class FakeRecord:
    item_type: type[Harvestable]
    remote_id: str | None
    item_processor_exception: Exception | None = None
    inner_harvest_exception: Exception | None = None

    @staticmethod
    def create(item_type: type[Harvestable], num: int) -> list["FakeRecord"]:
        return [FakeRecord(item_type, f"{item_type.__name__.lower()}-{i}") for i in range(num)]


H = TypeVar("H", bound=Harvestable)


class FakeBackend(BaseBackend):
    name = "fake-backend"
    display_name = "Fake Backend"
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
        self.fake_records = list[FakeRecord]()
        self.fake_last_modified: datetime | None = None

    @override
    def inner_harvest(self):
        self._fake_records_by_ids = {
            r.remote_id: r for r in self.fake_records if r.remote_id is not None
        }

        for record in self.fake_records:
            if exc := record.inner_harvest_exception:
                raise exc
            processor = getattr(self, f"process_{record.item_type.__name__.lower()}")
            self.process_item(record.remote_id, processor)

    def process_dataset(self, harvest_item: HarvestItem) -> Dataset:
        fields = DatasetFactory.as_dict(visible=True).items()
        return self._process_item(Dataset, fields, harvest_item.remote_id)

    def process_dataservice(self, harvest_item: HarvestItem) -> Dataservice:
        fields = DataserviceFactory.as_dict().items()
        return self._process_item(Dataservice, fields, harvest_item.remote_id)

    def _process_item(self, item_type: type[H], fields: dict, remote_id: str) -> H:
        record = self._fake_records_by_ids[remote_id]
        if exc := record.item_processor_exception:
            raise exc
        item = self.get_item(remote_id, item_type)
        self._mock_item(item, fields)
        return item

    def _mock_item(self, item, fields):
        for key, value in fields:
            if getattr(item, key) is None:
                setattr(item, key, value)
        if self.fake_last_modified:
            item.last_modified_internal = self.fake_last_modified
        clazz = type(item).__name__.lower()
        position = len(self.job.items)
        item.harvest.remote_url = f"http://www.example.com/records/{clazz}-url-{position}"


class FetchingBackend(FakeBackend):
    """A backend that really goes over the network, to exercise the HTTP layer."""

    name = "fetching-backend"

    def inner_harvest(self):
        self.get(self.source.url)


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
        backend = FakeBackend(source)
        backend.fake_records = FakeRecord.create(Dataset, nb_datasets)

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
        backend = FakeBackend(HarvestSourceFactory())
        assert not backend.has_feature("feature")
        assert backend.has_feature("enabled")

    def test_has_feature_defined(self):
        backend = FakeBackend(
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
        backend = FakeBackend(HarvestSourceFactory())
        with pytest.raises(HarvestException):
            backend.has_feature("unknown")

    def test_get_filters_empty(self):
        backend = FakeBackend(HarvestSourceFactory())
        assert backend.get_filters() == []

    def test_get_filters(self):
        backend = FakeBackend(
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
        backend = FakeBackend(HarvestSourceFactory())
        assert backend.get_extra_config_value("test_str") is None

    def test_get_extra_config_value(self):
        backend = FakeBackend(
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
        backend = FakeBackend(HarvestSourceFactory())
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
        backend = FakeBackend(HarvestSourceFactory())
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

        job = FetchingBackend(source).harvest()

        assert job.status == "failed"
        assert "10.0.0.1" in job.errors[0].message

    def test_harvest_item_remote_url(self):
        n = 3
        backend = FakeBackend(HarvestSourceFactory())
        backend.fake_records = FakeRecord.create(Dataset, n) + FakeRecord.create(Dataservice, n)

        job = backend.harvest()

        assert len(job.items) == 2 * n
        assert all([item.remote_url for item in job.items])

    def test_harvest_source_id(self):
        nb_datasets = 3
        source = HarvestSourceFactory()
        backend = FakeBackend(source)
        backend.fake_records = FakeRecord.create(Dataset, nb_datasets)

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
        backend = FakeBackend(HarvestSourceFactory())
        backend.fake_records = FakeRecord.create(Dataset, 1)
        backend.fake_last_modified = last_modified

        backend.harvest()
        dataset = Dataset.objects.first()
        assert_equal_dates(dataset.last_modified_internal, last_modified)
        assert_equal_dates(dataset.harvest.last_update, datetime.now(UTC))

    def test_dont_overwrite_last_modified_even_if_set_to_same(self):
        last_modified = faker.date_time_between(start_date="-30y", end_date="-1y")
        backend = FakeBackend(HarvestSourceFactory())
        backend.fake_records = FakeRecord.create(Dataset, 1)
        backend.fake_last_modified = last_modified

        backend.harvest()
        backend.harvest()  # Harvest twice to test same last_modified
        dataset = Dataset.objects.first()
        assert_equal_dates(dataset.last_modified_internal, last_modified)
        assert_equal_dates(dataset.harvest.last_update, datetime.now(UTC))

    def test_autoarchive(self, app):
        nb_datasets = 3
        nb_dataservices = 3
        source = HarvestSourceFactory()
        backend = FakeBackend(source)
        backend.fake_records = FakeRecord.create(Dataset, nb_datasets) + FakeRecord.create(
            Dataservice, nb_dataservices
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
        backend = FakeBackend(HarvestSourceFactory())
        backend.fake_records = FakeRecord.create(Dataset, 3)

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
        backend = FakeBackend(source)
        backend.fake_records = FakeRecord.create(Dataset, nb_datasets) + [
            FakeRecord(Dataset, duplicated_remote_id_uri)
        ]

        # Create a dataset that should be reused by the harvest, which will update it
        # instead of creating a new one, as it has the same remote_id, domain and source_id.
        dataset_reused = DatasetFactory(
            title="Reused Dataset",
            harvest={
                "domain": source.domain,
                "remote_id": "dataset-0",  # the FakeBackend harvest should reuse this dataset
                "source_id": str(source.id),
            },
        )
        # Create a dataset that should be reused even though it's a different `source_id` and `domain,
        # because the remote_id is the same and an URI.
        dataset_reused_uri = DatasetFactory(
            title="Reused Dataset with URI",
            harvest={
                "domain": "some-other-domain",
                # the FakeBackend harvest above should reuse this dataset with the same remote_id URI
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
            FakeRecord(Dataset, "dataset-id-1"),
            FakeRecord(Dataset, "dataset-id-2"),
            FakeRecord(Dataset, "dataset-id-3"),
            FakeRecord(Dataset, "dataset-id-3"),
            FakeRecord(Dataset, "dataset-id-1"),
        ]
        dataservice_records = [
            FakeRecord(Dataservice, "dataservice-id-1"),
            FakeRecord(Dataservice, "dataservice-id-2"),
            FakeRecord(Dataservice, "dataservice-id-2"),
        ]
        backend = FakeBackend(HarvestSourceFactory())
        backend.fake_records = dataset_records + dataservice_records

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
        backend1 = FakeBackend(
            HarvestSourceFactory(
                url="https://data.example.com/catalog",
                **{owner_param: owner_factory()},
            )
        )
        backend1.fake_records = [
            FakeRecord(Dataset, "https://data.example.com/catalog/dataset-repeat"),
            FakeRecord(Dataset, "https://data.example.com/catalog/dataset-unique"),
            # dataservices don't check on uri remote_id (bug?)
        ]

        job1 = backend1.harvest()
        assert job1.status == "done"
        assert len(job1.items) == 2

        backend2 = FakeBackend(
            HarvestSourceFactory(
                url="https://other.example.com/catalog",
                **{owner_param: owner_factory()},
            )
        )
        backend2.fake_records = [
            FakeRecord(Dataset, "https://data.example.com/catalog/dataset-repeat"),
            FakeRecord(Dataset, "https://other.example.com/catalog/dataset-unique"),
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
        backend1 = FakeBackend(
            HarvestSourceFactory(
                url="https://data.example.com/catalog",
                **{owner_param: owner_factory()},
            )
        )
        backend1.fake_records = [
            FakeRecord(Dataset, "dataset-repeat"),
            FakeRecord(Dataset, "dataset-unique-1"),
            FakeRecord(Dataservice, "dataservice-repeat"),
            FakeRecord(Dataservice, "dataservice-unique-1"),
        ]

        job1 = backend1.harvest()
        assert job1.status == "done"
        assert len(job1.items) == 4

        backend2 = FakeBackend(
            HarvestSourceFactory(
                url="https://data.example.com/other-catalog",  # same domain as backend1
                **{owner_param: owner_factory()},
            )
        )
        backend2.fake_records = [
            FakeRecord(Dataset, "dataset-repeat"),
            FakeRecord(Dataset, "dataset-unique-2"),
            FakeRecord(Dataservice, "dataservice-repeat"),
            FakeRecord(Dataservice, "dataservice-unique-2"),
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
        "max_items, n_dataset, n_dataservice",
        [(2, 2, 0), (3, 3, 0), (4, 3, 1)],
    )
    def test_max_items(self, max_items, n_dataset, n_dataservice):
        backend = FakeBackend(HarvestSourceFactory(), max_items=max_items)
        backend.fake_records = FakeRecord.create(Dataset, 3) + FakeRecord.create(Dataservice, 3)

        job = backend.harvest()
        assert job.status == "done"
        assert len(job.items) == max_items
        assert len(job.errors) == 1
        assert job.errors[0].message.startswith(f"{max_items} max items reached")
        assert Dataset.objects.count() == n_dataset
        assert Dataservice.objects.count() == n_dataservice

    def test_max_items_preview(self):
        backend = FakeBackend(HarvestSourceFactory(), dryrun=True, max_items=2)
        backend.fake_records = FakeRecord.create(Dataset, 3) + FakeRecord.create(Dataservice, 3)

        job = backend.harvest()
        assert job.status == "done"
        assert len(job.items) == 2
        # we don't log the max_items error in dryrun
        assert len(job.errors) == 0

    @pytest.mark.parametrize(
        "exception_class",
        [
            HarvestValidationError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            Exception,
        ],
    )
    def test_inner_harvest_exception(self, exception_class):
        backend = FakeBackend(HarvestSourceFactory())
        backend.fake_records = [
            FakeRecord(Dataset, "dataset-ok-1"),
            FakeRecord(Dataset, "dataset-ko", inner_harvest_exception=exception_class()),
            FakeRecord(Dataset, "dataset-ok-2"),
        ]

        job = backend.harvest()
        assert job.status == "failed"
        assert len(job.errors) == 1
        assert len(job.items) == 1

    @pytest.mark.parametrize(
        "exception_class, job_status, item_status",
        [
            (HarvestSkipException, "done", "skipped"),
            (HarvestValidationError, "done-errors", "failed"),
            (Exception, "done-errors", "failed"),
        ],
    )
    def test_item_processor_exception(self, exception_class, job_status, item_status):
        backend = FakeBackend(HarvestSourceFactory())
        backend.fake_records = [
            FakeRecord(Dataset, "dataset-ok-1"),
            FakeRecord(Dataset, "dataset-ko", item_processor_exception=exception_class()),
            FakeRecord(Dataset, "dataset-ok-2"),
        ]

        job = backend.harvest()
        assert job.status == job_status
        assert len(job.errors) == 0
        assert len(job.items) == 3
        assert job.items[1].status == item_status


class BaseBackendValidateTest(PytestOnlyDBTestCase):
    @pytest.fixture
    def validate(self):
        return FakeBackend(HarvestSourceFactory()).validate

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
