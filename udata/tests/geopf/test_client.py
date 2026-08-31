import io
from unittest.mock import patch

import pytest

from udata.geopf.client import (
    GeopfClient,
    GeopfError,
    GeopfTimeoutError,
    _extract_file_identifier,
    _TimeoutSession,
)
from udata.tests import PytestOnlyTestCase
from udata.tests.geopf import (
    TEST_API_BASE,
    TEST_API_URL,
    TEST_DATASTORE_ID,
    TEST_GEOPF_CONF,
    TEST_TOKEN,
)

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
        uid = GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).create_upload(
            "name", "description"
        )
        assert uid == "upload-1"

    def test_create_upload_raises_on_http_error(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads", status_code=500, text="server error")
        with pytest.raises(GeopfError):
            GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).create_upload(
                "name", "description"
            )

    def test_error_body_is_truncated(self, rmock):
        """The response body is stored and re-exposed via the public status API, so an
        untrusted, oversized upstream error body must not be repeated in full."""
        rmock.post(f"{TEST_API_URL}/uploads", status_code=500, text="x" * 2000)
        with pytest.raises(GeopfError) as exc_info:
            GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).create_upload(
                "name", "description"
            )
        assert str(exc_info.value).endswith("x" * 500 + "…")
        assert len(str(exc_info.value)) < 600

    def test_push_file_sends_path_param(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads/u1/data", json={})
        GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).push_file(
            "u1", io.BytesIO(b"data"), "test.gpkg"
        )
        assert "path=%2Ftest.gpkg" in rmock.last_request.url

    def test_push_md5_includes_checksum_line(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads/u1/md5", json={})
        GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).push_md5(
            "u1", "test.gpkg", "abc123"
        )
        assert b"abc123  test.gpkg" in rmock.last_request.body

    def test_close_upload(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads/u1/close", json={})
        GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).close_upload("u1")
        assert rmock.called

    def test_delete_upload(self, rmock):
        rmock.delete(f"{TEST_API_URL}/uploads/u1", json={})
        GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).delete_upload("u1")
        assert rmock.called

    def test_poll_upload_closed_when_no_pending_checks(self, rmock):
        rmock.get(
            f"{TEST_API_URL}/uploads/u1/checks",
            json={"asked": [], "in_progress": [], "failed": []},
        )
        status = GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).poll_upload("u1")
        assert status == "CLOSED"

    def test_poll_upload_unstable_when_failed(self, rmock):
        rmock.get(
            f"{TEST_API_URL}/uploads/u1/checks",
            json={"failed": [{"id": "c1"}], "asked": [], "in_progress": []},
        )
        status = GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).poll_upload("u1")
        assert status == "UNSTABLE"

    @pytest.mark.options(GEOPF_POLL_TIMEOUT=-1)
    def test_poll_upload_raises_timeout_error(self, rmock):
        with pytest.raises(GeopfTimeoutError):
            GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).poll_upload("u1")


@TEST_GEOPF_CONF
class GeopfClientProcessingTest(PytestOnlyTestCase):
    def test_launch_processing_returns_exec_id(self, rmock):
        rmock.get(
            f"{TEST_API_URL}/processings",
            json=[
                {
                    "_id": "proc-raster",
                    "input_types": {"upload": ["RASTER"]},
                    "output_type": {"stored_data": "ROK4-PYRAMID-RASTER"},
                },
                # this one will be found by input/ouput types
                {
                    "_id": "proc-vector",
                    "input_types": {"upload": ["VECTOR"]},
                    "output_type": {"stored_data": "VECTOR-DB"},
                },
            ],
        )
        rmock.post(f"{TEST_API_URL}/processings/executions", json={"_id": "exec-1"})
        rmock.post(f"{TEST_API_URL}/processings/executions/exec-1/launch", json={})
        exec_id = GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).launch_processing(
            "u1", "stored-name"
        )
        assert exec_id == "exec-1"
        executions_request = next(
            r for r in rmock.request_history if r.url.endswith("/processings/executions")
        )
        assert executions_request.json()["processing"] == "proc-vector"

        processings_request = next(
            r for r in rmock.request_history if r.path.endswith("/processings")
        )
        assert "fields=input_types%2coutput_types" in processings_request.query

    def test_launch_processing_raises_when_no_matching_processing(self, rmock):
        rmock.get(
            f"{TEST_API_URL}/processings",
            json=[
                {
                    "_id": "proc-raster",
                    "input_types": {"upload": ["RASTER"]},
                    "output_type": {"stored_data": "ROK4-PYRAMID-RASTER"},
                }
            ],
        )
        with pytest.raises(GeopfError, match="No VECTOR"):
            GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).launch_processing(
                "u1", "stored-name"
            )

    def test_poll_execution_success(self, rmock):
        rmock.get(
            f"{TEST_API_URL}/processings/executions/exec-1",
            json={"status": "SUCCESS", "output": {"stored_data": {"_id": "sd-1"}}},
        )
        status, sd_id = GeopfClient(
            token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID
        ).poll_execution("exec-1")
        assert status == "SUCCESS"
        assert sd_id == "sd-1"

    def test_poll_execution_failure(self, rmock):
        rmock.get(f"{TEST_API_URL}/processings/executions/exec-1", json={"status": "FAILURE"})
        status, sd_id = GeopfClient(
            token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID
        ).poll_execution("exec-1")
        assert status == "FAILURE"
        assert sd_id is None

    def test_poll_execution_aborted(self, rmock):
        rmock.get(f"{TEST_API_URL}/processings/executions/exec-1", json={"status": "ABORTED"})
        status, sd_id = GeopfClient(
            token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID
        ).poll_execution("exec-1")
        assert status == "ABORTED"
        assert sd_id is None

    @pytest.mark.options(GEOPF_POLL_TIMEOUT=-1)
    def test_poll_execution_raises_timeout_error(self, rmock):
        with pytest.raises(GeopfTimeoutError):
            GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).poll_execution("exec-1")


@TEST_GEOPF_CONF
class GeopfClientTaggingTest(PytestOnlyTestCase):
    def test_tag_entity_sends_datasheet_name(self, rmock):
        rmock.post(f"{TEST_API_URL}/uploads/u1/tags", json={})
        GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).tag_entity(
            "uploads", "u1", "my-sheet"
        )
        assert rmock.last_request.json() == {"datasheet_name": "my-sheet"}


@TEST_GEOPF_CONF
class GeopfClientOfferingsTest(PytestOnlyTestCase):
    def test_list_offerings_returns_list(self, rmock):
        offerings = [{"_id": "o1", "type": "WFS"}]
        rmock.get(f"{TEST_API_URL}/offerings", json=offerings)
        result = GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).list_offerings(
            "sd-1"
        )
        assert result == offerings

    def test_list_offerings_follows_content_range_pagination(self, rmock):
        page1 = [{"_id": f"o{i}"} for i in range(10)]
        page2 = [{"_id": "o10"}]
        rmock.get(
            f"{TEST_API_URL}/offerings",
            [
                {"json": page1, "headers": {"Content-Range": "0-9/11"}},
                {"json": page2, "headers": {"Content-Range": "10-10/11"}},
            ],
        )
        result = GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).list_offerings(
            "sd-1"
        )
        assert result == page1 + page2
        assert rmock.call_count == 2
        assert rmock.request_history[0].qs["page"] == ["1"]
        assert rmock.request_history[1].qs["page"] == ["2"]


@TEST_GEOPF_CONF
class GeopfClientMetadataTest(PytestOnlyTestCase):
    def test_upload_metadata_returns_new_id(self, rmock):
        rmock.post(f"{TEST_API_URL}/metadata", json={"_id": "meta-1"})
        mid = GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).upload_metadata(
            TEST_METADATA_XML
        )
        assert mid == "meta-1"

    def test_upload_metadata_409_updates_existing(self, rmock):
        rmock.post(f"{TEST_API_URL}/metadata", status_code=409, text="conflict")
        rmock.get(
            f"{TEST_API_URL}/metadata",
            json=[{"_id": "meta-existing", "file_identifier": "fid-1"}],
        )
        rmock.put(f"{TEST_API_URL}/metadata/meta-existing", json={})
        mid = GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).upload_metadata(
            TEST_METADATA_XML
        )
        assert mid == "meta-existing"

    def test_upload_metadata_409_no_match_raises(self, rmock):
        rmock.post(f"{TEST_API_URL}/metadata", status_code=409, text="conflict")
        rmock.get(f"{TEST_API_URL}/metadata", json=[])
        with pytest.raises(GeopfError):
            GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).upload_metadata(
                TEST_METADATA_XML
            )

    def test_upload_metadata_409_no_match_truncates_body(self, rmock):
        rmock.post(f"{TEST_API_URL}/metadata", status_code=409, text="x" * 1000)
        rmock.get(f"{TEST_API_URL}/metadata", json=[])
        with pytest.raises(GeopfError, match="x" * 500 + "…"):
            GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).upload_metadata(
                TEST_METADATA_XML
            )

    def test_update_metadata_returns_id(self, rmock):
        rmock.put(f"{TEST_API_URL}/metadata/meta-1", json={})
        mid = GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).update_metadata(
            "meta-1", TEST_METADATA_XML
        )
        assert mid == "meta-1"


class ExtractFileIdentifierTest:
    def test_extracts_id_from_valid_xml(self):
        assert _extract_file_identifier(TEST_METADATA_XML) == "fid-1"

    def test_raises_when_element_missing(self):
        with pytest.raises(GeopfError):
            _extract_file_identifier(b"<root/>")


@TEST_GEOPF_CONF
class GeopfClientDatastoresTest(PytestOnlyTestCase):
    def test_list_datastores_returns_full_rights_memberships(self, rmock):
        rmock.get(
            f"{TEST_API_BASE}/users/me",
            json={
                "communities_member": [
                    {
                        "rights": ["UPLOAD", "PROCESSING", "BROADCAST"],
                        "community": {"datastore": "ds-1", "name": "my-entrepot"},
                    }
                ]
            },
        )
        result = GeopfClient(token=TEST_TOKEN).list_datastores()
        assert result == [
            {
                "datastore_id": "ds-1",
                "name": "my-entrepot",
                "rights": ["UPLOAD", "PROCESSING", "BROADCAST"],
            }
        ]

    def test_list_datastores_excludes_partial_rights_memberships(self, rmock):
        rmock.get(
            f"{TEST_API_BASE}/users/me",
            json={
                "communities_member": [
                    {
                        "rights": ["UPLOAD", "COMMUNITY"],
                        "community": {"datastore": "ds-readonly", "name": "not-publishable"},
                    }
                ]
            },
        )
        result = GeopfClient(token=TEST_TOKEN).list_datastores()
        assert result == []

    def test_list_datastores_empty_when_no_memberships(self, rmock):
        rmock.get(f"{TEST_API_BASE}/users/me", json={})
        result = GeopfClient(token=TEST_TOKEN).list_datastores()
        assert result == []


@TEST_GEOPF_CONF
class GeopfClientAuthTest(PytestOnlyTestCase):
    def test_token_sends_bearer_authorization_header(self, rmock):
        rmock.get(f"{TEST_API_URL}/offerings", json=[])
        GeopfClient(token=TEST_TOKEN, datastore_id=TEST_DATASTORE_ID).list_offerings("sd-1")
        assert rmock.last_request.headers["Authorization"] == f"Bearer {TEST_TOKEN}"

    def test_no_datastore_id_raises_on_datastore_scoped_call(self):
        with pytest.raises(GeopfError):
            GeopfClient(token=TEST_TOKEN).list_offerings("sd-1")


class TimeoutSessionTest(PytestOnlyTestCase):
    def test_applies_default_timeout(self):
        session = _TimeoutSession(timeout=42)
        with patch("requests.Session.request") as mock_request:
            session.get("https://example.com")
        assert mock_request.call_args.kwargs["timeout"] == 42

    def test_explicit_timeout_is_not_overridden(self):
        session = _TimeoutSession(timeout=42)
        with patch("requests.Session.request") as mock_request:
            session.get("https://example.com", timeout=5)
        assert mock_request.call_args.kwargs["timeout"] == 5
