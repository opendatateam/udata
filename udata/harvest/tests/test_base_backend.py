from datetime import datetime, timedelta
from urllib.parse import urlparse

import pytest
from voluptuous import Schema

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataset import tasks
from udata.core.dataset.factories import DatasetFactory
from udata.harvest.models import HarvestItem
from udata.models import Dataset
from udata.tests.helpers import assert_equal_dates
from udata.utils import faker

from ..backends import BaseBackend, HarvestExtraConfig, HarvestFeature, HarvestFilter
from ..exceptions import HarvestException
from .factories import HarvestSourceFactory


class Unknown:
    pass


def gen_remote_IDs(num: int, prefix: str = "") -> list[str]:
    """Generate remote IDs."""
    return [f"{prefix}fake-{i}" for i in range(num)]


class FakeBackend(BaseBackend):
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

    def inner_harvest(self):
        for remote_id in self.source.config.get("dataset_remote_ids", []):
            self.process_dataset(remote_id)
            if self.has_reached_max_items():
                return

        for remote_id in self.source.config.get("dataservice_remote_ids", []):
            self.process_dataservice(remote_id)
            if self.has_reached_max_items():
                return

    def inner_process_dataset(self, item: HarvestItem):
        dataset = self.get_dataset(item.remote_id)

        for key, value in DatasetFactory.as_dict(visible=True).items():
            if getattr(dataset, key) is None:
                setattr(dataset, key, value)
        if self.source.config.get("last_modified"):
            dataset.last_modified_internal = self.source.config["last_modified"]
        return dataset

    def inner_process_dataservice(self, item: HarvestItem):
        dataservice = self.get_dataservice(item.remote_id)

        for key, value in DataserviceFactory.as_dict().items():
            if getattr(dataservice, key) is None:
                setattr(dataservice, key, value)
        if self.source.config.get("last_modified"):
            dataservice.last_modified_internal = self.source.config["last_modified"]
        return dataservice


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


@pytest.mark.usefixtures("clean_db")
class BaseBackendTest:
    def test_simple_harvest(self):
        now = datetime.utcnow()
        nb_datasets = 3
        source = HarvestSourceFactory(config={"dataset_remote_ids": gen_remote_IDs(nb_datasets)})
        backend = FakeBackend(source)

        job = backend.harvest()

        assert len(job.items) == nb_datasets
        assert Dataset.objects.count() == nb_datasets
        for dataset in Dataset.objects():
            assert_equal_dates(dataset.last_modified, now)
            assert dataset.harvest.source_id == str(source.id)
            assert dataset.harvest.domain == source.domain
            assert dataset.harvest.remote_id.startswith("fake-")
            assert_equal_dates(dataset.harvest.last_update, now)

    def test_has_feature_defaults(self):
        source = HarvestSourceFactory()
        backend = FakeBackend(source)

        assert not backend.has_feature("feature")
        assert backend.has_feature("enabled")

    def test_has_feature_defined(self):
        source = HarvestSourceFactory(
            config={
                "features": {
                    "feature": True,
                    "enabled": False,
                }
            }
        )
        backend = FakeBackend(source)

        assert backend.has_feature("feature")
        assert not backend.has_feature("enabled")

    def test_has_feature_unkown(self):
        source = HarvestSourceFactory()
        backend = FakeBackend(source)

        with pytest.raises(HarvestException):
            backend.has_feature("unknown")

    def test_get_filters_empty(self):
        source = HarvestSourceFactory()
        backend = FakeBackend(source)

        assert backend.get_filters() == []

    def test_get_filters(self):
        source = HarvestSourceFactory(
            config={
                "filters": [
                    {"key": "second", "value": ""},
                    {"key": "first", "value": ""},
                ]
            }
        )
        backend = FakeBackend(source)

        assert [f["key"] for f in backend.get_filters()] == ["second", "first"]

    def test_get_extra_config_not_in_source(self):
        source = HarvestSourceFactory()
        backend = FakeBackend(source)
        assert backend.get_extra_config_value("test_str") is None

    def test_get_extra_config_value(self):
        source = HarvestSourceFactory(
            config={
                "extra_configs": [
                    {"key": "test_str", "value": "test"},
                ]
            }
        )
        backend = FakeBackend(source)
        assert backend.get_extra_config_value("test_str") == "test"

    def test_harvest_source_id(self):
        nb_datasets = 3
        source = HarvestSourceFactory(config={"dataset_remote_ids": gen_remote_IDs(nb_datasets)})
        backend = FakeBackend(source)

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

    def test_dont_overwrite_last_modified(self, mocker):
        last_modified = faker.date_time_between(start_date="-30y", end_date="-1y")
        source = HarvestSourceFactory(
            config={"dataset_remote_ids": gen_remote_IDs(1), "last_modified": last_modified}
        )
        backend = FakeBackend(source)

        backend.harvest()

        dataset = Dataset.objects.first()

        assert_equal_dates(dataset.last_modified_internal, last_modified)
        assert_equal_dates(dataset.harvest.last_update, datetime.utcnow())

    def test_dont_overwrite_last_modified_even_if_set_to_same(self, mocker):
        last_modified = faker.date_time_between(start_date="-30y", end_date="-1y")
        source = HarvestSourceFactory(
            config={"dataset_remote_ids": gen_remote_IDs(1), "last_modified": last_modified}
        )
        backend = FakeBackend(source)

        backend.harvest()
        backend.harvest()  # Harvest twice to test same last_modified

        dataset = Dataset.objects.first()

        assert_equal_dates(dataset.last_modified_internal, last_modified)
        assert_equal_dates(dataset.harvest.last_update, datetime.utcnow())

    def test_autoarchive(self, app):
        nb_datasets = 3
        nb_dataservices = 3
        source = HarvestSourceFactory(
            config={
                "dataset_remote_ids": gen_remote_IDs(nb_datasets, "dataset-"),
                "dataservice_remote_ids": gen_remote_IDs(nb_dataservices, "dataservice-"),
            }
        )
        backend = FakeBackend(source)

        # create a dangling dataset to be archived
        limit = app.config["HARVEST_AUTOARCHIVE_GRACE_DAYS"]
        last_update = datetime.utcnow() - timedelta(days=limit + 1)
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
        last_update = datetime.utcnow() - timedelta(days=limit - 1)
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
        assert "archived" in dataset_arch.harvest
        assert "archived_at" in dataset_arch.harvest

        dataset_no_arch.reload()
        assert dataset_no_arch.archived is None
        assert "archived" not in dataset_no_arch.harvest
        assert "archived_at" not in dataset_no_arch.harvest

        dataservice_arch.reload()
        assert dataservice_arch.archived_at is not None
        assert "archived_reason" in dataservice_arch.harvest
        assert "archived_at" in dataservice_arch.harvest

        dataservice_no_arch.reload()
        assert dataservice_no_arch.archived_at is None
        assert "archived_reason" not in dataservice_no_arch.harvest
        assert "archived_at" not in dataservice_no_arch.harvest

        # test unarchive: archive manually then relaunch harvest
        dataset = Dataset.objects.get(**{"harvest__remote_id": "dataset-fake-1"})
        dataset.archived = datetime.utcnow()
        dataset.harvest.archived = "not-on-remote"
        dataset.harvest.archived_at = datetime.utcnow()
        dataset.save()

        dataservice = Dataservice.objects.get(**{"harvest__remote_id": "dataservice-fake-1"})
        dataservice.archived_at = datetime.utcnow()
        dataservice.harvest.archived_reason = "not-on-remote"
        dataservice.harvest.archived_at = datetime.utcnow()
        dataservice.save()

        backend.harvest()

        dataset.reload()
        assert dataset.archived is None
        assert "archived" not in dataset.harvest
        assert "archived_at" not in dataset.harvest

        dataservice.reload()
        assert dataservice.archived_at is None
        assert "archived_reason" not in dataservice.harvest
        assert "archived_at" not in dataservice.harvest

    def test_harvest_datasets_get_deleted(self):
        nb_datasets = 3
        source = HarvestSourceFactory(config={"dataset_remote_ids": gen_remote_IDs(nb_datasets)})
        backend = FakeBackend(source)

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
        remote_ids = gen_remote_IDs(nb_datasets)
        remote_ids.append(duplicated_remote_id_uri)
        source = HarvestSourceFactory(config={"dataset_remote_ids": remote_ids})
        backend = FakeBackend(source)

        # Create a dataset that should be reused by the harvest, which will update it
        # instead of creating a new one, as it has the same remote_id, domain and source_id.
        dataset_reused = DatasetFactory(
            title="Reused Dataset",
            harvest={
                "domain": source.domain,
                "remote_id": "fake-0",  # the FakeBackend harvest should reuse this dataset
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
                "remote_id": "fake-0",  # the "source" harvest above should create another dataset with the same remote_id
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
            Dataset.objects(harvest__remote_id="fake-0").count() == 2
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


@pytest.mark.usefixtures("clean_db")
class BaseBackendValidateTest:
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
