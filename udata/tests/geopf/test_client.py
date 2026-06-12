import io

import pytest

from udata.geopf.client import (
    GeopfClient,
    GeopfError,
    GeopfTimeoutError,
    _extract_file_identifier,
)
from udata.tests import PytestOnlyTestCase
from udata.tests.geopf import TEST_API_URL, TEST_GEOPF_CONF

# Minimal valid ISO 19115 XML fragment used by several metadata tests
TEST_METADATA_XML = (
    b'<?xml version="1.0"?>'
    b'<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"'
    b' xmlns:gco="http://www.isotc211.org/2005/gco">'
    b"<gmd:fileIdentifier><gco:CharacterString>fid-1</gco:CharacterString>"
    b"</gmd:fileIdentifier></gmd:MD_Metadata>"
)


@TEST_GEOPF_CONF
class GeopfClientUploadTest(PytestOnlyTestCase):
    def test_create_upload_returns_id(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads", json={"_id": "upload-1"})
        uid = GeopfClient().create_upload("name", "description")
        assert uid == "upload-1"

    def test_create_upload_raises_on_http_error(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads", status_code=500, text="server error")
        with pytest.raises(GeopfError):
            GeopfClient().create_upload("name", "description")

    def test_push_file_sends_path_param(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads/u1/data", json={})
        GeopfClient().push_file("u1", io.BytesIO(b"data"), "test.gpkg")
        assert "path=%2Ftest.gpkg" in rmock.last_request.url

    def test_push_md5_includes_checksum_line(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads/u1/md5", json={})
        GeopfClient().push_md5("u1", "test.gpkg", "abc123")
        assert b"abc123  test.gpkg" in rmock.last_request.body

    def test_close_upload(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads/u1/close", json={})
        GeopfClient().close_upload("u1")
        assert rmock.called

    def test_delete_upload(self, rmock):
        rmock.delete(f"{TEST_API_URL}/uploads/u1", json={})
        GeopfClient().delete_upload("u1")
        assert rmock.called

    def test_poll_upload_closed_when_no_pending_checks(self, rmock):
        rmock.get(
            f"{TEST_API_URL}/uploads/u1/checks",
            json={"asked": [], "in_progress": [], "failed": []},
        )
        status = GeopfClient().poll_upload("u1")
        assert status == "CLOSED"

    def test_poll_upload_unstable_when_failed(self, rmock):
        rmock.get(
            f"{TEST_API_URL}/uploads/u1/checks",
            json={"failed": [{"id": "c1"}], "asked": [], "in_progress": []},
        )
        status = GeopfClient().poll_upload("u1")
        assert status == "UNSTABLE"

    @pytest.mark.options(GEOPF_POLL_TIMEOUT=-1)
    def test_poll_upload_raises_on_timeout(self, rmock):
        with pytest.raises(GeopfError):
            GeopfClient().poll_upload("u1")


@TEST_GEOPF_CONF
class GeopfClientProcessingTest(PytestOnlyTestCase):
    def test_launch_processing_returns_exec_id(self, rmock):
        rmock.post(f"{TEST_API_URL}/processings/executions", json={"_id": "exec-1"})
        rmock.post(f"{TEST_API_URL}/processings/executions/exec-1/launch", json={})
        exec_id = GeopfClient().launch_processing("u1", "stored-name")
        assert exec_id == "exec-1"

    def test_poll_execution_success(self, rmock):
        rmock.get(
            f"{TEST_API_URL}/processings/executions/exec-1",
            json={"status": "SUCCESS", "output": {"stored_data": {"_id": "sd-1"}}},
        )
        status, sd_id = GeopfClient().poll_execution("exec-1")
        assert status == "SUCCESS"
        assert sd_id == "sd-1"

    def test_poll_execution_failure(self, rmock):
        rmock.get(f"{TEST_API_URL}/processings/executions/exec-1", json={"status": "FAILURE"})
        status, sd_id = GeopfClient().poll_execution("exec-1")
        assert status == "FAILURE"
        assert sd_id is None

    def test_poll_execution_aborted(self, rmock):
        rmock.get(f"{TEST_API_URL}/processings/executions/exec-1", json={"status": "ABORTED"})
        status, sd_id = GeopfClient().poll_execution("exec-1")
        assert status == "ABORTED"
        assert sd_id is None

    @pytest.mark.options(GEOPF_POLL_TIMEOUT=-1)
    def test_poll_execution_raises_timeout_error(self, rmock):
        with pytest.raises(GeopfTimeoutError):
            GeopfClient().poll_execution("exec-1")


@TEST_GEOPF_CONF
class GeopfClientTaggingTest(PytestOnlyTestCase):
    def test_tag_entity_sends_datasheet_name(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads/u1/tags", json={})
        GeopfClient().tag_entity("uploads", "u1", "my-sheet")
        assert rmock.last_request.json() == {"datasheet_name": "my-sheet"}


@TEST_GEOPF_CONF
class GeopfClientOfferingsTest(PytestOnlyTestCase):
    def test_list_offerings_returns_list(self, rmock):
        offerings = [{"_id": "o1", "type": "WFS"}]
        rmock.get(f"{TEST_API_URL}/offerings", json=offerings)
        result = GeopfClient().list_offerings("sd-1")
        assert result == offerings


@TEST_GEOPF_CONF
class GeopfClientMetadataTest(PytestOnlyTestCase):
    def test_upload_metadata_returns_new_id(self, rmock):
        rmock.post(f"{TEST_API_URL}/metadata", json={"_id": "meta-1"})
        mid = GeopfClient().upload_metadata(TEST_METADATA_XML)
        assert mid == "meta-1"

    def test_upload_metadata_409_updates_existing(self, rmock):
        rmock.post(f"{TEST_API_URL}/metadata", status_code=409, text="conflict")
        rmock.get(
            f"{TEST_API_URL}/metadata",
            json=[{"_id": "meta-existing", "file_identifier": "fid-1"}],
        )
        rmock.put(f"{TEST_API_URL}/metadata/meta-existing", json={})
        mid = GeopfClient().upload_metadata(TEST_METADATA_XML)
        assert mid == "meta-existing"

    def test_upload_metadata_409_no_match_raises(self, rmock):
        rmock.post(f"{TEST_API_URL}/metadata", status_code=409, text="conflict")
        rmock.get(f"{TEST_API_URL}/metadata", json=[])
        with pytest.raises(GeopfError):
            GeopfClient().upload_metadata(TEST_METADATA_XML)

    def test_update_metadata_returns_id(self, rmock):
        rmock.put(f"{TEST_API_URL}/metadata/meta-1", json={})
        mid = GeopfClient().update_metadata("meta-1", TEST_METADATA_XML)
        assert mid == "meta-1"


class ExtractFileIdentifierTest:
    def test_extracts_id_from_valid_xml(self):
        assert _extract_file_identifier(TEST_METADATA_XML) == "fid-1"

    def test_raises_when_element_missing(self):
        with pytest.raises(GeopfError):
            _extract_file_identifier(b"<root/>")
