import io
import logging
import re
import time
from typing import IO
from xml.etree.ElementTree import fromstring

import requests
from flask import current_app

from udata.geopf.metadata import XML_NS
from udata.geopf.srs import DEFAULT_SRS

log = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds between status checks

# Error response bodies are stored and re-exposed via the public status API ,
# so bound how much of an untrusted upstream response we repeat (avoids sensitive tracebacks)
ERROR_BODY_LIMIT = 500


def _truncate_body(text: str) -> str:
    if len(text) > ERROR_BODY_LIMIT:
        return text[:ERROR_BODY_LIMIT] + "…"
    return text


# Community rights (per GET /users/me's communities_member[].rights) needed to
# fully complete the push pipeline: upload, processing, and a visible offering.
REQUIRED_PUBLISH_RIGHTS = {"UPLOAD", "PROCESSING", "BROADCAST"}

# geopf paginates listing endpoints and reports progress via a
# `Content-Range: <min>-<max>/<total>` response header.
CONTENT_RANGE_RE = re.compile(r"(?P<min>\d+)-(?P<max>\d+)/(?P<total>\d+)")


class GeopfError(Exception):
    pass


class GeopfTimeoutError(GeopfError):
    """Raised when a polled operation does not complete within the configured timeout."""

    pass


class GeopfReauthRequired(GeopfError):
    """Raised when there is no valid (or refreshable) geopf token for the acting user."""

    pass


class _TimeoutSession(requests.Session):
    """A requests.Session with a default per-request timeout."""

    def __init__(self, timeout: float):
        super().__init__()
        self.default_timeout = timeout

    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", self.default_timeout)
        return super().request(*args, **kwargs)


class GeopfClient:
    def __init__(self, token: str, datastore_id: str | None = None):
        """A geopf entrepôt API client.

        `token` is the acting user's bearer access token: every call here
        (push, reverse sync alike) runs as whichever user is currently
        authenticated, there is no anonymous or service-account credential.
        `datastore_id` scopes datastore-bound calls (uploads, processing,
        tagging, metadata, offerings); it isn't needed for instance-level
        calls like `list_datastores`.
        """
        self.base = current_app.config["GEOPF_API_BASE"]
        self.datastore = datastore_id
        self.poll_timeout = current_app.config["GEOPF_POLL_TIMEOUT"]
        self.session = _TimeoutSession(timeout=current_app.config["GEOPF_REQUEST_TIMEOUT"])
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _url(self, path: str) -> str:
        if not self.datastore:
            raise GeopfError("GeopfClient: no datastore_id configured for this call")
        return f"{self.base}/datastores/{self.datastore}/{path}"

    def _raise(self, resp: requests.Response) -> None:
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise GeopfError(f"{resp.status_code} {resp.url}: {_truncate_body(resp.text)}") from e

    # --- livraison ---

    def create_upload(self, name: str, description: str, srs: str = DEFAULT_SRS) -> str:
        resp = self.session.post(
            self._url("uploads"),
            json={"name": name, "type": "VECTOR", "srs": srs, "description": description},
        )
        self._raise(resp)
        return resp.json()["_id"]

    def push_file(self, upload_id: str, fileobj: IO[bytes], filename: str) -> None:
        resp = self.session.post(
            self._url(f"uploads/{upload_id}/data"),
            params={"path": f"/{filename}"},
            files={"file": (filename, fileobj, "application/octet-stream")},
        )
        self._raise(resp)

    def push_md5(self, upload_id: str, filename: str, md5: str) -> None:
        content = f"{md5}  {filename}\n"
        resp = self.session.post(
            self._url(f"uploads/{upload_id}/md5"),
            files={"file": ("checksums.md5", io.BytesIO(content.encode()), "text/plain")},
        )
        self._raise(resp)

    def close_upload(self, upload_id: str) -> None:
        resp = self.session.post(self._url(f"uploads/{upload_id}/close"))
        self._raise(resp)

    def poll_upload(self, upload_id: str) -> str:
        """Poll /checks until all checks complete. Returns 'CLOSED' or 'UNSTABLE'."""
        deadline = time.time() + self.poll_timeout
        while time.time() < deadline:
            resp = self.session.get(self._url(f"uploads/{upload_id}/checks"))
            self._raise(resp)
            data = resp.json()
            if data.get("failed"):
                return "UNSTABLE"
            if not data.get("asked") and not data.get("in_progress"):
                return "CLOSED"
            time.sleep(POLL_INTERVAL)
        raise GeopfTimeoutError(
            f"Upload {upload_id} checks did not complete within {self.poll_timeout}s"
        )

    def delete_upload(self, upload_id: str) -> None:
        resp = self.session.delete(self._url(f"uploads/{upload_id}"))
        self._raise(resp)

    # --- processing ---

    def _find_vector_processing_id(self) -> str:
        """Find this datastore's registered "vector integration" processing.

        Processing ids are per-datastore, not global (sandbox entrepôts don't
        carry the same ids as production ones), so there is no single id that
        works everywhere. Matched by type rather than name (a human label, not
        guaranteed stable or unique): the one whose input accepts a VECTOR
        upload and whose output is a VECTOR-DB stored_data.
        """
        resp = self.session.get(
            self._url("processings"),
            # "output_types" (plural) is the query param's name per geopf's API;
            # the response field it populates is "output_type" (singular).
            params={"fields": "input_types,output_types", "limit": 100},
        )
        self._raise(resp)
        for processing in resp.json():
            input_types = processing.get("input_types") or {}
            output_type = processing.get("output_type") or {}
            if (
                "VECTOR" in (input_types.get("upload") or [])
                and output_type.get("stored_data") == "VECTOR-DB"
            ):
                return processing["_id"]
        raise GeopfError(
            f"No VECTOR -> VECTOR-DB processing available on datastore {self.datastore}"
        )

    def launch_processing(
        self, upload_id: str, stored_data_name: str, srs: str = DEFAULT_SRS
    ) -> str:
        payload = {
            "processing": self._find_vector_processing_id(),
            "inputs": {"upload": [upload_id]},
            "output": {"stored_data": {"name": stored_data_name}},
            "parameters": {"srs": srs},
        }
        resp = self.session.post(self._url("processings/executions"), json=payload)
        self._raise(resp)
        exec_id = resp.json()["_id"]

        resp = self.session.post(self._url(f"processings/executions/{exec_id}/launch"))
        self._raise(resp)
        return exec_id

    def poll_execution(self, exec_id: str) -> tuple[str, str | None]:
        """Poll until the execution finishes. Returns (status, stored_data_id)."""
        deadline = time.time() + self.poll_timeout
        while time.time() < deadline:
            resp = self.session.get(self._url(f"processings/executions/{exec_id}"))
            self._raise(resp)
            data = resp.json()
            status = data["status"]
            if status == "SUCCESS":
                return status, data["output"]["stored_data"]["_id"]
            if status in ("FAILURE", "ABORTED"):
                return status, None
            time.sleep(POLL_INTERVAL)
        raise GeopfTimeoutError(f"Execution {exec_id} did not complete within {self.poll_timeout}s")

    # --- tagging ---

    def tag_entity(self, entity_type: str, entity_id: str, datasheet_name: str) -> None:
        # entity_type: "uploads", "stored_data", "metadata"
        resp = self.session.post(
            self._url(f"{entity_type}/{entity_id}/tags"),
            json={"datasheet_name": datasheet_name},
        )
        self._raise(resp)

    # --- datastores ---

    def list_datastores(self) -> list:
        """Return the datastores (entrepôts) the current user has full publish rights on.

        geopf has no datastore-scoped listing endpoint; discovered instead via
        `GET /users/me` -> `communities_member[].community.datastore`, each
        membership carrying its own `rights`. Full publish rights means
        UPLOAD (livraison), PROCESSING (vector integration) and BROADCAST
        (making the resulting offering visible) are all present together;
        a membership missing any of those can't complete the push pipeline,
        so it's filtered out here rather than surfaced as a dead end.
        """
        resp = self.session.get(f"{self.base}/users/me")
        self._raise(resp)
        memberships = resp.json().get("communities_member", [])
        return [
            {
                "datastore_id": m["community"]["datastore"],
                "name": m["community"].get("name"),
                "rights": m.get("rights", []),
            }
            for m in memberships
            if REQUIRED_PUBLISH_RIGHTS.issubset(m.get("rights", []))
        ]

    # --- offerings ---

    def list_offerings(self, stored_data_id: str) -> list:
        """Return all offerings for a stored_data, including urls and type."""
        offerings = []
        page = 1
        while True:
            resp = self.session.get(
                self._url("offerings"),
                params={
                    "stored_data": stored_data_id,
                    "fields": "urls,type,layer_name,status,open",
                    "page": page,
                },
            )
            self._raise(resp)
            body = resp.json()
            offerings += body
            match = CONTENT_RANGE_RE.search(resp.headers.get("Content-Range", ""))
            if not match or len(offerings) >= int(match["total"]):
                return offerings
            page += 1

    # --- metadata ---

    def upload_metadata(self, xml_bytes: bytes) -> str:
        """Upload metadata, updating in-place if the file_identifier already exists."""
        resp = self.session.post(
            self._url("metadata"),
            data={"type": "ISOAP", "open_data": "true"},
            files={"file": ("metadata.xml", io.BytesIO(xml_bytes), "application/xml")},
        )
        if resp.status_code == 409:
            fid = _extract_file_identifier(xml_bytes)
            existing_id = self._find_metadata_id(fid)
            if existing_id:
                return self.update_metadata(existing_id, xml_bytes)
            raise GeopfError(
                f"409 on metadata upload, could not locate existing record: "
                f"{_truncate_body(resp.text)}"
            )
        self._raise(resp)
        return resp.json()["_id"]

    def _find_metadata_id(self, file_identifier: str) -> str | None:
        resp = self.session.get(self._url("metadata"), params={"file_identifier": file_identifier})
        self._raise(resp)
        # `file_identifier` can be a partial match, need to check equality
        for item in resp.json():
            if item.get("file_identifier") == file_identifier:
                return item["_id"]
        return None

    def update_metadata(self, metadata_id: str, xml_bytes: bytes) -> str:
        resp = self.session.put(
            self._url(f"metadata/{metadata_id}"),
            files={"file": ("metadata.xml", io.BytesIO(xml_bytes), "application/xml")},
        )
        self._raise(resp)
        return metadata_id


def _extract_file_identifier(xml_bytes: bytes) -> str:
    el = fromstring(xml_bytes).find("gmd:fileIdentifier/gco:CharacterString", XML_NS)
    if el is None or not el.text:
        raise GeopfError("Could not extract file_identifier from metadata XML")
    return el.text
