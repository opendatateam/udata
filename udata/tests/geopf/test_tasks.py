from unittest.mock import MagicMock, patch

import pytest

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.geopf.client import GeopfError, GeopfTimeoutError
from udata.geopf.metadata import SANDBOX_DATASTORE_ID
from udata.geopf.tasks import (
    _download_to_tempfile,
    _offering_url,
    _resource_filename,
    pull_offerings_for_dataset,
    pull_offerings_from_geopf,
    push_resource_to_geopf,
    sync_metadata,
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


class DownloadToTempfileTest(PytestOnlyTestCase):
    def test_downloads_within_size_limit(self, rmock):
        rmock.get("https://example.com/data.gpkg", content=b"x" * 1024)
        with _download_to_tempfile("https://example.com/data.gpkg") as f:
            assert f.read() == b"x" * 1024

    @pytest.mark.options(GEOPF_MAX_REMOTE_FILE_SIZE=1024)
    def test_raises_when_size_limit_exceeded(self, rmock):
        rmock.get("https://example.com/data.gpkg", content=b"x" * 2048)
        with pytest.raises(GeopfError, match="GEOPF_MAX_REMOTE_FILE_SIZE"):
            with _download_to_tempfile("https://example.com/data.gpkg"):
                pass


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

    def test_prefixes_file_identifier_on_sandbox_datastore(self):
        dataset = DatasetFactory()
        client = MagicMock(datastore=SANDBOX_DATASTORE_ID)
        client.upload_metadata.return_value = "meta-new"

        sync_metadata(dataset, client)

        xml_bytes = client.upload_metadata.call_args[0][0]
        assert f"SANDBOX_{dataset.id}".encode() in xml_bytes

    def test_does_not_prefix_file_identifier_on_other_datastores(self):
        dataset = DatasetFactory()
        client = MagicMock(datastore="some-other-datastore")
        client.upload_metadata.return_value = "meta-new"

        sync_metadata(dataset, client)

        xml_bytes = client.upload_metadata.call_args[0][0]
        assert f"SANDBOX_{dataset.id}".encode() not in xml_bytes
        assert str(dataset.id).encode() in xml_bytes


@TEST_GEOPF_CONF
class PullOfferingsTest(PytestOnlyDBTestCase):
    def test_no_stored_data_skips_api_call(self):
        dataset = DatasetFactory()

        with patch("udata.geopf.tasks.GeopfClient") as mock_client_cls:
            count = pull_offerings_for_dataset(dataset, TEST_TOKEN)

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
            count = pull_offerings_for_dataset(dataset, TEST_TOKEN)

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

    def test_skips_when_no_datastore_pinned(self):
        # no geopf:push:datastore-id: dataset was never successfully pushed
        gpkg = ResourceFactory.build(format="gpkg", extras={"geopf:push:stored-data-id": "sd-1"})
        dataset = DatasetFactory(resources=[gpkg])

        with patch("udata.geopf.tasks.GeopfClient") as mock_client_cls:
            count = pull_offerings_for_dataset(dataset, TEST_TOKEN)

        assert count == 0
        mock_client_cls.assert_not_called()

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
            pull_offerings_for_dataset(dataset, TEST_TOKEN)

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
            count = pull_offerings_for_dataset(dataset, TEST_TOKEN)

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
                args=[str(dataset.id), resource_id],
                kwargs={"access_token": "test-token", "datastore_id": TEST_DATASTORE_ID},
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
                    kwargs={"access_token": "test-token", "datastore_id": TEST_DATASTORE_ID},
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
                    kwargs={"access_token": "test-token", "datastore_id": TEST_DATASTORE_ID},
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
                args=[str(dataset.id), resource_id],
                kwargs={"access_token": "test-token", "datastore_id": TEST_DATASTORE_ID},
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

    def test_failed_push_does_not_persist_datastore_id(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline", side_effect=GeopfError("boom")):
            with pytest.raises(GeopfError):
                push_resource_to_geopf.apply(
                    args=[str(dataset.id), resource_id],
                    kwargs={"access_token": "test-token", "datastore_id": "ds-bad"},
                    throw=True,
                )

        dataset.reload()
        assert "geopf:push:datastore-id" not in dataset.extras

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


class PushResourceTaskSkipTest(PytestOnlyDBTestCase):
    """Task early-return paths that need no GEOPF credentials configured."""

    def test_skips_when_no_datastore_id_resolvable(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline") as mock_pipeline:
            push_resource_to_geopf.apply(args=[str(dataset.id), resource_id])

        mock_pipeline.assert_not_called()


@TEST_GEOPF_CONF
class PullOfferingsTaskTest(PytestOnlyDBTestCase):
    def test_sets_pending_then_done_on_success(self):
        dataset = DatasetFactory()

        with patch("udata.geopf.tasks.pull_offerings_for_dataset", return_value=3):
            pull_offerings_from_geopf.apply(
                args=[str(dataset.id)], kwargs={"access_token": "test-token"}, throw=True
            )

        dataset.reload()
        assert dataset.extras.get("geopf:pull:status") == "done"
        assert "geopf:pull:last-synced-at" in dataset.extras

    def test_sets_error_status_on_failure(self):
        dataset = DatasetFactory()

        with patch("udata.geopf.tasks.pull_offerings_for_dataset", side_effect=GeopfError("boom")):
            with pytest.raises(GeopfError):
                pull_offerings_from_geopf.apply(
                    args=[str(dataset.id)],
                    kwargs={"access_token": "test-token"},
                    throw=True,
                )

        dataset.reload()
        assert dataset.extras.get("geopf:pull:status") == "error"
        assert "boom" in dataset.extras.get("geopf:pull:error", "")
