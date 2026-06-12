from unittest.mock import MagicMock, patch

import pytest

import udata.geopf  # noqa: F401 — registers on_resource_added signal handler
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.dataset.models import Resource
from udata.geopf import _should_push
from udata.geopf.client import GeopfError, GeopfTimeoutError
from udata.geopf.tasks import (
    _offering_url,
    _resource_filename,
    push_resource_to_geopf,
    sync_metadata,
    sync_services_for_dataset,
)
from udata.tests import PytestOnlyTestCase
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.geopf import TEST_GEOPF_CONF


class ShouldPushTest(PytestOnlyTestCase):
    def test_gpkg_no_status_is_true(self):
        assert _should_push(Resource(format="gpkg", url="http://files.example.com/f.gpkg"))

    def test_gpkg_uppercase_is_true(self):
        assert _should_push(Resource(format="GPKG", url="http://files.example.com/f.gpkg"))

    def test_non_gpkg_is_false(self):
        assert not _should_push(Resource(format="csv", url="http://files.example.com/f.csv"))

    def test_no_format_is_false(self):
        assert not _should_push(Resource(url="http://files.example.com/f.gpkg"))

    def test_gpkg_with_existing_status_is_false(self):
        r = Resource(format="gpkg", url="http://files.example.com/f.gpkg")
        r.extras["geopf:push:status"] = "done"
        assert not _should_push(r)

    def test_none_is_false(self):
        assert not _should_push(None)


class OfferingUrlTest:
    def test_returns_first_url(self):
        offering = {"urls": [{"url": "http://wfs.example.com"}, {"url": "http://wms.example.com"}]}
        assert _offering_url(offering) == "http://wfs.example.com"

    def test_empty_urls_returns_empty_string(self):
        assert _offering_url({"urls": []}) == ""

    def test_no_urls_key_returns_empty_string(self):
        assert _offering_url({}) == ""


class ResourceFilenameTest(PytestOnlyTestCase):
    def test_from_fs_filename(self):
        r = ResourceFactory.build(fs_filename="uploads/2024/01/my-data.gpkg")
        assert _resource_filename(r) == "my-data.gpkg"

    def test_from_url(self):
        r = ResourceFactory.build(fs_filename=None, url="https://example.com/data/france.gpkg")
        assert _resource_filename(r) == "france.gpkg"

    def test_url_no_path_falls_back_to_resource_id(self):
        r = ResourceFactory.build(fs_filename=None, url="https://example.com")
        assert _resource_filename(r).endswith(".gpkg")


class SyncMetadataTest(PytestOnlyDBTestCase):
    def test_new_metadata_uploads_and_persists_id(self):
        dataset = DatasetFactory()
        client = MagicMock()
        client.upload_metadata.return_value = "meta-new"

        result = sync_metadata(dataset, client)

        assert result == "meta-new"
        client.upload_metadata.assert_called_once()
        client.tag_entity.assert_called_once_with("metadata", "meta-new", str(dataset.id))
        dataset.reload()
        assert dataset.extras.get("geopf:push:metadata-id") == "meta-new"

    def test_existing_metadata_updates_without_re_tagging(self):
        dataset = DatasetFactory(extras={"geopf:push:metadata-id": "meta-old"})
        client = MagicMock()

        result = sync_metadata(dataset, client)

        assert result == "meta-old"
        client.update_metadata.assert_called_once()
        client.upload_metadata.assert_not_called()
        client.tag_entity.assert_not_called()


class SyncServicesTest(PytestOnlyDBTestCase):
    def test_no_stored_data_skips_api_call(self):
        dataset = DatasetFactory()
        client = MagicMock()

        count = sync_services_for_dataset(dataset, client)

        assert count == 0
        client.list_offerings.assert_not_called()

    def test_adds_resource_for_new_offering(self):
        gpkg = ResourceFactory.build(format="gpkg", extras={"geopf:push:stored-data-id": "sd-1"})
        dataset = DatasetFactory(resources=[gpkg])
        client = MagicMock()
        client.list_offerings.return_value = [
            {
                "_id": "offer-1",
                "type": "WFS",
                "layer_name": "layer1",
                "urls": [{"url": "http://wfs.example.com"}],
            }
        ]

        count = sync_services_for_dataset(dataset, client)

        assert count == 1
        dataset.reload()
        offering_resource = next(
            (r for r in dataset.resources if r.extras.get("geopf:offering:id") == "offer-1"),
            None,
        )
        assert offering_resource is not None
        assert offering_resource.url == "http://wfs.example.com"
        assert offering_resource.format == "wfs"

    def test_updates_url_for_changed_offering(self):
        gpkg = ResourceFactory.build(format="gpkg", extras={"geopf:push:stored-data-id": "sd-1"})
        stale_service = ResourceFactory.build(
            url="http://old.example.com/wfs",
            filetype="remote",
            type="api",
            extras={"geopf:offering:id": "offer-1"},
        )
        dataset = DatasetFactory(resources=[gpkg, stale_service])
        client = MagicMock()
        client.list_offerings.return_value = [
            {
                "_id": "offer-1",
                "type": "WFS",
                "layer_name": "layer1",
                "urls": [{"url": "http://new.example.com/wfs"}],
            }
        ]

        sync_services_for_dataset(dataset, client)

        dataset.reload()
        resource = next(
            r for r in dataset.resources if r.extras.get("geopf:offering:id") == "offer-1"
        )
        assert resource.url == "http://new.example.com/wfs"

    def test_removes_resource_for_deleted_offering(self):
        gpkg = ResourceFactory.build(format="gpkg", extras={"geopf:push:stored-data-id": "sd-1"})
        gone_service = ResourceFactory.build(
            filetype="remote",
            type="api",
            extras={"geopf:offering:id": "offer-gone"},
        )
        dataset = DatasetFactory(resources=[gpkg, gone_service])
        client = MagicMock()
        client.list_offerings.return_value = []

        count = sync_services_for_dataset(dataset, client)

        assert count == 0
        dataset.reload()
        assert not any(r.extras.get("geopf:offering:id") for r in dataset.resources)


@TEST_GEOPF_CONF
class PushResourceTaskTest(PytestOnlyDBTestCase):
    def test_sets_pending_then_done_on_success(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline"):
            push_resource_to_geopf.apply(args=[str(dataset.id), resource_id])

        dataset.reload()
        r = next(r for r in dataset.resources if str(r.id) == resource_id)
        assert r.extras.get("geopf:push:status") == "pending"

    def test_sets_error_status_on_pipeline_failure(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline", side_effect=GeopfError("boom")):
            with pytest.raises(GeopfError):
                push_resource_to_geopf.apply(args=[str(dataset.id), resource_id], throw=True)

        dataset.reload()
        r = next(r for r in dataset.resources if str(r.id) == resource_id)
        assert r.extras.get("geopf:push:status") == "error"
        assert "boom" in r.extras.get("geopf:push:error", "")

    def test_sets_timeout_status_on_pipeline_timeout(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline", side_effect=GeopfTimeoutError("timed out")):
            with pytest.raises(GeopfTimeoutError):
                push_resource_to_geopf.apply(args=[str(dataset.id), resource_id], throw=True)

        dataset.reload()
        r = next(r for r in dataset.resources if str(r.id) == resource_id)
        assert r.extras.get("geopf:push:status") == "timeout"

    def test_skips_non_gpkg_resource(self):
        resource = ResourceFactory.build(format="csv", url="http://files.example.com/f.csv")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline") as mock_pipeline:
            push_resource_to_geopf.apply(args=[str(dataset.id), resource_id])

        mock_pipeline.assert_not_called()


@pytest.mark.options(GEOPF_TOKEN=None, GEOPF_DATASTORE_ID=None)
class PushResourceTaskSkipTest(PytestOnlyDBTestCase):
    """Task early-return paths that need no GEOPF credentials configured."""

    def test_skips_when_config_missing(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline") as mock_pipeline:
            push_resource_to_geopf.apply(args=[str(dataset.id), resource_id])

        mock_pipeline.assert_not_called()


class OnResourceAddedSignalTest(PytestOnlyDBTestCase):
    def test_queues_push_for_gpkg_resource(self):
        dataset = DatasetFactory()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")

        with patch("udata.geopf.tasks.push_resource_to_geopf.delay") as mock_delay:
            dataset.add_resource(resource)

        mock_delay.assert_called_once_with(str(dataset.id), str(resource.id))

    def test_does_not_queue_for_non_gpkg(self):
        dataset = DatasetFactory()
        resource = ResourceFactory.build(format="csv", url="http://files.example.com/f.csv")

        with patch("udata.geopf.tasks.push_resource_to_geopf.delay") as mock_delay:
            dataset.add_resource(resource)

        mock_delay.assert_not_called()

    def test_does_not_queue_when_already_pushed(self):
        dataset = DatasetFactory()
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        resource.extras["geopf:push:status"] = "done"

        with patch("udata.geopf.tasks.push_resource_to_geopf.delay") as mock_delay:
            dataset.add_resource(resource)

        mock_delay.assert_not_called()
