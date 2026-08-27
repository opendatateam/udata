import io
from unittest.mock import MagicMock, patch

import pytest
from flask_storage.errors import OperationNotSupported

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.dataset.models import Dataset
from udata.core.user.factories import UserFactory
from udata.geopf.client import GeopfError, GeopfTimeoutError
from udata.geopf.models import (
    GeopfDatasetMetadata,
    GeopfDatasetPullMetadata,
    GeopfDatasetPushMetadata,
    GeopfResourceMetadata,
    GeopfResourceOfferingMetadata,
    GeopfResourcePushMetadata,
    dataset_push_metadata,
    resource_offering_metadata,
)
from udata.geopf.srs import DEFAULT_SRS
from udata.geopf.tasks import (
    _DownloadToTempfile,
    _LocalStorageToTempfile,
    _offering_url,
    _open_resource_file,
    _resource_filename,
    _run_pipeline,
    pull_offerings_for_dataset,
    pull_offerings_from_geopf,
    push_resource_to_geopf,
    set_dataset_pull_metadata,
    set_resource_push_metadata,
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
        with _DownloadToTempfile("https://example.com/data.gpkg") as f:
            assert f.read() == b"x" * 1024

    @pytest.mark.options(GEOPF_MAX_FILE_SIZE=1024)
    def test_raises_when_size_limit_exceeded(self, rmock):
        rmock.get("https://example.com/data.gpkg", content=b"x" * 2048)
        with pytest.raises(GeopfError, match="GEOPF_MAX_FILE_SIZE"):
            with _DownloadToTempfile("https://example.com/data.gpkg"):
                pass


class LocalStorageToTempfileTest(PytestOnlyTestCase):
    def test_yields_a_seekable_copy_regardless_of_backend(self):
        """The storage backend's own `.open()` may return a non-seekable stream (e.g. a
        botocore StreamingBody on S3): only chunked `.read(n)` is relied on here, and the
        result must support seeking back to the start, unlike that stream would."""
        with patch(
            "udata.geopf.tasks.storages.resources.open", return_value=io.BytesIO(b"x" * 1024)
        ):
            with _LocalStorageToTempfile("uploads/my-data.gpkg") as f:
                assert f.read() == b"x" * 1024
                f.seek(0)
                assert f.read() == b"x" * 1024

    @pytest.mark.options(GEOPF_MAX_FILE_SIZE=1024)
    def test_raises_when_size_limit_exceeded(self):
        """The same GEOPF_MAX_FILE_SIZE limit applies here as for remote downloads."""
        with patch(
            "udata.geopf.tasks.storages.resources.open", return_value=io.BytesIO(b"x" * 2048)
        ):
            with pytest.raises(GeopfError, match="GEOPF_MAX_FILE_SIZE"):
                with _LocalStorageToTempfile("uploads/my-data.gpkg"):
                    pass


class OpenResourceFileTest(PytestOnlyTestCase):
    def test_uses_the_real_path_directly_when_the_backend_supports_it(self):
        """The common case (e.g. the local backend): no copy, no temp file."""
        r = ResourceFactory.build(filetype="file", fs_filename="uploads/my-data.gpkg")
        with patch("udata.geopf.tasks.storages.resources.path", return_value=__file__) as mock_path:
            with _open_resource_file(r) as f:
                assert f.name == __file__
        mock_path.assert_called_once_with(r.fs_filename)

    def test_falls_back_to_a_copy_when_the_backend_has_no_direct_path(self):
        """E.g. the S3 backend: `.path()` raises `OperationNotSupported`."""
        r = ResourceFactory.build(filetype="file", fs_filename="uploads/my-data.gpkg")
        with patch("udata.geopf.tasks.storages.resources.path", side_effect=OperationNotSupported):
            with patch(
                "udata.geopf.tasks.storages.resources.open", return_value=io.BytesIO(b"x" * 16)
            ):
                with _open_resource_file(r) as f:
                    assert f.read() == b"x" * 16

    def test_downloads_remote_resources(self, rmock):
        r = ResourceFactory.build(
            filetype="remote", fs_filename=None, url="https://example.com/f.gpkg"
        )
        rmock.get("https://example.com/f.gpkg", content=b"x" * 16)
        with _open_resource_file(r) as f:
            assert f.read() == b"x" * 16


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
        assert dataset.geopf.push.metadata_id == "meta-new"

    def test_existing_metadata_updates_without_re_tagging(self):
        dataset = DatasetFactory(
            geopf=GeopfDatasetMetadata(push=GeopfDatasetPushMetadata(metadata_id="meta-old"))
        )
        client = MagicMock()

        result = sync_metadata(dataset, client)

        assert result == "meta-old"
        client.update_metadata.assert_called_once()
        client.upload_metadata.assert_not_called()
        client.tag_entity.assert_not_called()


class MetadataSettersTest(PytestOnlyDBTestCase):
    """A `None` value must unset the key, not write a literal `null` -- checked against raw BSON,
    since the marshalled response reads identically either way."""

    def test_none_unsets_dataset_field_rather_than_nulling_it(self):
        dataset = DatasetFactory(
            geopf=GeopfDatasetMetadata(pull=GeopfDatasetPullMetadata(error="previously boom"))
        )

        set_dataset_pull_metadata(dataset, error=None)

        raw = Dataset._get_collection().find_one({"_id": dataset.id})
        assert "error" not in raw["geopf"]["pull"]
        assert dataset.geopf.pull.error is None

    def test_none_unsets_resource_field_rather_than_nulling_it(self):
        resource = ResourceFactory.build(
            geopf=GeopfResourceMetadata(push=GeopfResourcePushMetadata(error="previously boom"))
        )
        dataset = DatasetFactory(resources=[resource])
        resource = dataset.resources[0]

        set_resource_push_metadata(dataset, resource, error=None)

        raw = Dataset._get_collection().find_one({"_id": dataset.id})
        assert "error" not in raw["resources"][0]["geopf"]["push"]
        assert dataset.resources[0].geopf.push.error is None


@TEST_GEOPF_CONF
class PullOfferingsTest(PytestOnlyDBTestCase):
    def test_no_stored_data_skips_api_call(self):
        dataset = DatasetFactory()

        with patch("udata.geopf.tasks.GeopfClient") as mock_client_cls:
            count = pull_offerings_for_dataset(dataset, TEST_TOKEN)

        assert count == 0
        mock_client_cls.assert_not_called()

    def test_adds_resource_for_new_offering(self):
        gpkg = ResourceFactory.build(
            format="gpkg",
            geopf=GeopfResourceMetadata(push=GeopfResourcePushMetadata(stored_data_id="sd-1")),
        )
        dataset = DatasetFactory(
            resources=[gpkg],
            geopf=GeopfDatasetMetadata(push=GeopfDatasetPushMetadata(datastore_id="ds-1")),
        )
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
            (r for r in dataset.resources if resource_offering_metadata(r).id == "offer-1"),
            None,
        )
        assert offering_resource is not None
        assert offering_resource.url == "http://wfs.example.com"
        assert offering_resource.format == "wfs"

    def test_skips_when_no_datastore_pinned(self):
        # no geopf.push.datastore_id: dataset was never successfully pushed
        gpkg = ResourceFactory.build(
            format="gpkg",
            geopf=GeopfResourceMetadata(push=GeopfResourcePushMetadata(stored_data_id="sd-1")),
        )
        dataset = DatasetFactory(resources=[gpkg])

        with patch("udata.geopf.tasks.GeopfClient") as mock_client_cls:
            count = pull_offerings_for_dataset(dataset, TEST_TOKEN)

        assert count == 0
        mock_client_cls.assert_not_called()

    def test_updates_url_for_changed_offering(self):
        gpkg = ResourceFactory.build(
            format="gpkg",
            geopf=GeopfResourceMetadata(push=GeopfResourcePushMetadata(stored_data_id="sd-1")),
        )
        stale_offering = ResourceFactory.build(
            url="http://old.example.com/wfs",
            filetype="remote",
            type="api",
            geopf=GeopfResourceMetadata(offering=GeopfResourceOfferingMetadata(id="offer-1")),
        )
        dataset = DatasetFactory(
            resources=[gpkg, stale_offering],
            geopf=GeopfDatasetMetadata(push=GeopfDatasetPushMetadata(datastore_id="ds-1")),
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
            r for r in dataset.resources if resource_offering_metadata(r).id == "offer-1"
        )
        assert resource.url == "http://new.example.com/wfs"

    def test_removes_resource_for_deleted_offering(self):
        gpkg = ResourceFactory.build(
            format="gpkg",
            geopf=GeopfResourceMetadata(push=GeopfResourcePushMetadata(stored_data_id="sd-1")),
        )
        gone_offering = ResourceFactory.build(
            filetype="remote",
            type="api",
            geopf=GeopfResourceMetadata(offering=GeopfResourceOfferingMetadata(id="offer-gone")),
        )
        dataset = DatasetFactory(
            resources=[gpkg, gone_offering],
            geopf=GeopfDatasetMetadata(push=GeopfDatasetPushMetadata(datastore_id="ds-1")),
        )
        mock_client = MagicMock()
        mock_client.list_offerings.return_value = []

        with patch("udata.geopf.tasks.GeopfClient", return_value=mock_client):
            count = pull_offerings_for_dataset(dataset, TEST_TOKEN)

        assert count == 0
        dataset.reload()
        assert not any(resource_offering_metadata(r).id for r in dataset.resources)


@TEST_GEOPF_CONF
class RunPipelineTest(PytestOnlyDBTestCase):
    def test_sets_done_status_and_last_synced_at_on_success(self):
        resource = ResourceFactory.build(format="csv", url="http://files.example.com/f.csv")
        dataset = DatasetFactory(resources=[resource])
        resource = dataset.resources[0]

        client = MagicMock(datastore="ds-1")
        client.create_upload.return_value = "upload-1"
        client.poll_upload.return_value = "CLOSED"
        client.launch_processing.return_value = "exec-1"
        client.poll_execution.return_value = ("SUCCESS", "sd-1")
        client.upload_metadata.return_value = "meta-1"

        with patch("udata.geopf.tasks._open_resource_file") as mock_open_file:
            mock_open_file.return_value.__enter__.return_value = io.BytesIO(b"fake-bytes")
            _run_pipeline(dataset, resource, "ds-1", client)

        client.delete_upload.assert_called_once_with("upload-1")
        client.create_upload.assert_called_once_with(
            name=f"_{resource.id}", description=dataset.title, srs=DEFAULT_SRS
        )
        client.launch_processing.assert_called_once_with(
            "upload-1", f"_{resource.id}", srs=DEFAULT_SRS
        )
        dataset.reload()
        r = next(r for r in dataset.resources if r.id == resource.id)
        assert r.geopf.push.status == "done"
        assert r.geopf.push.stored_data_id == "sd-1"
        assert r.geopf.push.last_synced_at is not None
        assert dataset.geopf.push.fiche_url

    def test_leaves_upload_in_place_on_timeout(self):
        resource = ResourceFactory.build(format="csv", url="http://files.example.com/f.csv")
        dataset = DatasetFactory(resources=[resource])
        resource = dataset.resources[0]

        client = MagicMock(datastore="ds-1")
        client.create_upload.return_value = "upload-1"
        client.poll_upload.return_value = "CLOSED"
        client.launch_processing.return_value = "exec-1"
        client.poll_execution.side_effect = GeopfTimeoutError("still running")

        with patch("udata.geopf.tasks._open_resource_file") as mock_open_file:
            mock_open_file.return_value.__enter__.return_value = io.BytesIO(b"fake-bytes")
            with pytest.raises(GeopfTimeoutError):
                _run_pipeline(dataset, resource, "ds-1", client)

        client.delete_upload.assert_not_called()

    def test_cleans_up_orphaned_upload_on_pipeline_failure(self):
        resource = ResourceFactory.build(format="csv", url="http://files.example.com/f.csv")
        dataset = DatasetFactory(resources=[resource])
        resource = dataset.resources[0]

        client = MagicMock(datastore="ds-1")
        client.create_upload.return_value = "upload-1"
        client.poll_upload.return_value = "CLOSED"
        client.launch_processing.side_effect = GeopfError("boom")

        with patch("udata.geopf.tasks._open_resource_file") as mock_open_file:
            mock_open_file.return_value.__enter__.return_value = io.BytesIO(b"fake-bytes")
            with pytest.raises(GeopfError):
                _run_pipeline(dataset, resource, "ds-1", client)

        client.delete_upload.assert_called_once_with("upload-1")


@TEST_GEOPF_CONF
class PushResourceTaskTest(PytestOnlyDBTestCase):
    def test_sets_pending_status_before_running_pipeline(self):
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
        assert r.geopf.push.status == "pending"

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
        assert r.geopf.push.status == "error"
        assert "boom" in (r.geopf.push.error or "")

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
        assert r.geopf.push.status == "timeout"

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
        assert dataset.geopf.push.datastore_id == "ds-1"

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
        assert dataset_push_metadata(dataset).datastore_id is None

    def test_subsequent_push_reuses_dataset_datastore_id(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(
            resources=[resource],
            geopf=GeopfDatasetMetadata(
                push=GeopfDatasetPushMetadata(datastore_id="ds-established")
            ),
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
        assert dataset.geopf.push.datastore_id == "ds-established"

    def test_skips_when_no_datastore_id_resolvable(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)

        with patch("udata.geopf.tasks._run_pipeline") as mock_pipeline:
            push_resource_to_geopf.apply(args=[str(dataset.id), resource_id])

        mock_pipeline.assert_not_called()

    def test_user_id_resolves_stored_token(self):
        resource = ResourceFactory.build(format="gpkg", url="http://files.example.com/f.gpkg")
        dataset = DatasetFactory(resources=[resource])
        resource_id = str(dataset.resources[0].id)
        user = UserFactory()

        with patch(
            "udata.geopf.tasks.resolve_access_token", return_value="resolved-token"
        ) as mock_resolve:
            with patch("udata.geopf.tasks.GeopfClient") as mock_client_cls:
                with patch("udata.geopf.tasks._run_pipeline"):
                    push_resource_to_geopf.apply(
                        args=[str(dataset.id), resource_id],
                        kwargs={"user_id": str(user.id), "datastore_id": TEST_DATASTORE_ID},
                    )

        mock_resolve.assert_called_once()
        assert mock_resolve.call_args.kwargs["user"].id == user.id
        mock_client_cls.assert_called_once_with(
            token="resolved-token", datastore_id=TEST_DATASTORE_ID
        )


@TEST_GEOPF_CONF
class PullOfferingsTaskTest(PytestOnlyDBTestCase):
    def test_sets_pending_then_done_on_success(self):
        dataset = DatasetFactory()

        with patch("udata.geopf.tasks.pull_offerings_for_dataset", return_value=3):
            pull_offerings_from_geopf.apply(
                args=[str(dataset.id)], kwargs={"access_token": "test-token"}, throw=True
            )

        dataset.reload()
        assert dataset.geopf.pull.status == "done"
        assert dataset.geopf.pull.last_synced_at is not None

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
        assert dataset.geopf.pull.status == "error"
        assert "boom" in (dataset.geopf.pull.error or "")

    def test_user_id_resolves_stored_token(self):
        dataset = DatasetFactory()
        user = UserFactory()

        with patch(
            "udata.geopf.tasks.resolve_access_token", return_value="resolved-token"
        ) as mock_resolve:
            with patch("udata.geopf.tasks.pull_offerings_for_dataset", return_value=0) as mock_pull:
                pull_offerings_from_geopf.apply(
                    args=[str(dataset.id)], kwargs={"user_id": str(user.id)}, throw=True
                )

        mock_resolve.assert_called_once()
        assert mock_resolve.call_args.kwargs["user"].id == user.id
        mock_pull.assert_called_once_with(dataset, "resolved-token")
