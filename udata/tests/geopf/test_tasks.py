from unittest.mock import MagicMock, patch

import pytest

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.geopf.client import GeopfError, GeopfTimeoutError
from udata.geopf.tasks import (
    _offering_url,
    _resource_filename,
    push_resource_to_geopf,
    sync_metadata,
    sync_offerings_for_dataset,
    sync_offerings_to_geopf,
)
from udata.tests import PytestOnlyTestCase
from udata.tests.api import PytestOnlyDBTestCase
from udata.tests.geopf import TEST_DATASTORE_ID, TEST_GEOPF_CONF, TEST_TOKEN


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


@TEST_GEOPF_CONF
class SyncOfferingsTest(PytestOnlyDBTestCase):
    def test_no_stored_data_skips_api_call(self):
        dataset = DatasetFactory()

        with patch("udata.geopf.tasks.GeopfClient") as mock_client_cls:
            count = sync_offerings_for_dataset(dataset, TEST_TOKEN)

        assert count == 0
        mock_client_cls.assert_not_called()

    def test_adds_resource_for_new_offering(self):
        gpkg = ResourceFactory.build(format="gpkg", extras={"geopf:push:stored-data-id": "sd-1"})
        dataset = DatasetFactory(resources=[gpkg], extras={"geopf:push:datastore-id": "ds-1"})
        mock_client = MagicMock()
        mock_client.list_offerings.return_value = [
            {
                "_id": "offer-1",
                "type": "WFS",
                "layer_name": "layer1",
                "urls": [{"url": "http://wfs.example.com"}],
            }
        ]

        with patch("udata.geopf.tasks.GeopfClient", return_value=mock_client) as mock_client_cls:
            count = sync_offerings_for_dataset(dataset, TEST_TOKEN)

        mock_client_cls.assert_called_once_with(token=TEST_TOKEN, datastore_id="ds-1")
        assert count == 1
        dataset.reload()
        offering_resource = next(
            (r for r in dataset.resources if r.extras.get("geopf:offering:id") == "offer-1"),
            None,
        )
        assert offering_resource is not None
        assert offering_resource.url == "http://wfs.example.com"
        assert offering_resource.format == "wfs"

    def test_falls_back_to_configured_datastore_id(self):
        # no geopf:push:datastore-id — dataset pushed before dataset-level tracking existed
        gpkg = ResourceFactory.build(format="gpkg", extras={"geopf:push:stored-data-id": "sd-1"})
        dataset = DatasetFactory(resources=[gpkg])
        mock_client = MagicMock()
        mock_client.list_offerings.return_value = []

        with patch("udata.geopf.tasks.GeopfClient", return_value=mock_client) as mock_client_cls:
            sync_offerings_for_dataset(dataset, TEST_TOKEN)

        mock_client_cls.assert_called_once_with(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID)

    def test_updates_url_for_changed_offering(self):
        gpkg = ResourceFactory.build(format="gpkg", extras={"geopf:push:stored-data-id": "sd-1"})
        stale_offering = ResourceFactory.build(
            url="http://old.example.com/wfs",
            filetype="remote",
            type="api",
            extras={"geopf:offering:id": "offer-1"},
        )
        dataset = DatasetFactory(
            resources=[gpkg, stale_offering], extras={"geopf:push:datastore-id": "ds-1"}
        )
        mock_client = MagicMock()
        mock_client.list_offerings.return_value = [
            {
                "_id": "offer-1",
                "type": "WFS",
                "layer_name": "layer1",
                "urls": [{"url": "http://new.example.com/wfs"}],
            }
        ]

        with patch("udata.geopf.tasks.GeopfClient", return_value=mock_client):
            sync_offerings_for_dataset(dataset, TEST_TOKEN)

        dataset.reload()
        resource = next(
            r for r in dataset.resources if r.extras.get("geopf:offering:id") == "offer-1"
        )
        assert resource.url == "http://new.example.com/wfs"

    def test_removes_resource_for_deleted_offering(self):
        gpkg = ResourceFactory.build(format="gpkg", extras={"geopf:push:stored-data-id": "sd-1"})
        gone_offering = ResourceFactory.build(
            filetype="remote",
            type="api",
            extras={"geopf:offering:id": "offer-gone"},
        )
        dataset = DatasetFactory(
            resources=[gpkg, gone_offering], extras={"geopf:push:datastore-id": "ds-1"}
        )
        mock_client = MagicMock()
        mock_client.list_offerings.return_value = []

        with patch("udata.geopf.tasks.GeopfClient", return_value=mock_client):
            count = sync_offerings_for_dataset(dataset, TEST_TOKEN)

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
            push_resource_to_geopf.apply(
                args=[str(dataset.id), resource_id], kwargs={"access_token": "test-token"}
            )

        dataset.reload()
        r = next(r for r in dataset.resources if str(r.id) == resource_id)
        assert r.extras.get("geopf:push:status") == "pending"

    def test_sets_error_status_on_pipeline_failure(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline", side_effect=GeopfError("boom")):
            with pytest.raises(GeopfError):
                push_resource_to_geopf.apply(
                    args=[str(dataset.id), resource_id],
                    kwargs={"access_token": "test-token"},
                    throw=True,
                )

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
                push_resource_to_geopf.apply(
                    args=[str(dataset.id), resource_id],
                    kwargs={"access_token": "test-token"},
                    throw=True,
                )

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

    @pytest.mark.options(GEOPF_PUSHABLE_FORMATS=frozenset({"gpkg", "csv"}))
    def test_pushes_format_allowed_by_config(self):
        resource = ResourceFactory.build(format="csv", url="http://files.example.com/f.csv")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline") as mock_pipeline:
            push_resource_to_geopf.apply(
                args=[str(dataset.id), resource_id], kwargs={"access_token": "test-token"}
            )

        mock_pipeline.assert_called_once()

    def test_first_push_persists_datastore_id_on_dataset(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline"):
            push_resource_to_geopf.apply(
                args=[str(dataset.id), resource_id],
                kwargs={"access_token": "test-token", "datastore_id": "ds-1"},
            )

        dataset.reload()
        assert dataset.extras.get("geopf:push:datastore-id") == "ds-1"

    def test_subsequent_push_reuses_dataset_datastore_id(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(
            resources=[resource], extras={"geopf:push:datastore-id": "ds-established"}
        )
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks.GeopfClient") as mock_client_cls:
            with patch("udata.geopf.tasks._run_pipeline"):
                push_resource_to_geopf.apply(
                    args=[str(dataset.id), resource_id],
                    # a different datastore_id is explicitly passed, but must be ignored
                    kwargs={"access_token": "test-token", "datastore_id": "ds-other"},
                )

        mock_client_cls.assert_called_once_with(token="test-token", datastore_id="ds-established")
        dataset.reload()
        assert dataset.extras.get("geopf:push:datastore-id") == "ds-established"


@pytest.mark.options(GEOPF_DATASTORE_ID=None)
class PushResourceTaskSkipTest(PytestOnlyDBTestCase):
    """Task early-return paths that need no GEOPF credentials configured."""

    def test_skips_when_config_missing(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline") as mock_pipeline:
            push_resource_to_geopf.apply(args=[str(dataset.id), resource_id])

        mock_pipeline.assert_not_called()


@TEST_GEOPF_CONF
class SyncOfferingsTaskTest(PytestOnlyDBTestCase):
    def test_sets_pending_then_done_on_success(self):
        dataset = DatasetFactory()

        with patch("udata.geopf.tasks.sync_offerings_for_dataset", return_value=3):
            sync_offerings_to_geopf.apply(
                args=[str(dataset.id)], kwargs={"access_token": "test-token"}, throw=True
            )

        dataset.reload()
        assert dataset.extras.get("geopf:pull:status") == "done"
        assert "geopf:pull:last-synced-at" in dataset.extras

    def test_sets_error_status_on_failure(self):
        dataset = DatasetFactory()

        with patch("udata.geopf.tasks.sync_offerings_for_dataset", side_effect=GeopfError("boom")):
            with pytest.raises(GeopfError):
                sync_offerings_to_geopf.apply(
                    args=[str(dataset.id)],
                    kwargs={"access_token": "test-token"},
                    throw=True,
                )

        dataset.reload()
        assert dataset.extras.get("geopf:pull:status") == "error"
        assert "boom" in dataset.extras.get("geopf:pull:error", "")
