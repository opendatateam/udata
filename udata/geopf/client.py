import io
import logging
import time
from xml.etree.ElementTree import fromstring

import requests
from flask import current_app

from udata.geopf.metadata import XML_NS

log = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds between status checks
POLL_TIMEOUT = 1800  # seconds, default 30 minutes; override via GEOPF_POLL_TIMEOUT config


class GeopfError(Exception):
    pass


class GeopfTimeoutError(GeopfError):
    """Raised when a polled operation does not complete within the configured timeout."""

    pass


class GeopfClient:
    def __init__(self):
        self.base = current_app.config["GEOPF_API_BASE"]
        self.datastore = current_app.config["GEOPF_DATASTORE_ID"]
        token = current_app.config["GEOPF_TOKEN"]
        self.poll_timeout = current_app.config.get("GEOPF_POLL_TIMEOUT", POLL_TIMEOUT)
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _url(self, path):
        return f"{self.base}/datastores/{self.datastore}/{path}"

    def _raise(self, resp):
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            raise GeopfError(f"{resp.status_code} {resp.url}: {resp.text}") from e

    # --- livraison ---

    def create_upload(self, name, description, srs="EPSG:4326"):
        resp = self.session.post(
            self._url("uploads"),
            json={"name": name, "type": "VECTOR", "srs": srs, "description": description},
        )
        self._raise(resp)
        return resp.json()["_id"]

    def push_file(self, upload_id, fileobj, filename):
        resp = self.session.post(
            self._url(f"uploads/{upload_id}/data"),
            params={"path": f"/{filename}"},
            files={"file": (filename, fileobj, "application/octet-stream")},
        )
        self._raise(resp)

    def push_md5(self, upload_id, filename, md5):
        content = f"{md5}  {filename}\n"
        resp = self.session.post(
            self._url(f"uploads/{upload_id}/md5"),
            files={"file": ("checksums.md5", io.BytesIO(content.encode()), "text/plain")},
        )
        self._raise(resp)

    def close_upload(self, upload_id):
        resp = self.session.post(self._url(f"uploads/{upload_id}/close"))
        self._raise(resp)

    def poll_upload(self, upload_id):
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
        raise GeopfError(f"Upload {upload_id} checks did not complete within {self.poll_timeout}s")

    def delete_upload(self, upload_id):
        resp = self.session.delete(self._url(f"uploads/{upload_id}"))
        self._raise(resp)

    # --- processing ---

    def launch_processing(self, upload_id, stored_data_name):
        processing_uuid = "0de8c60b-9938-4be9-aa36-9026b77c3c96"
        payload = {
            "processing": processing_uuid,
            "inputs": {"upload": [upload_id]},
            "output": {"stored_data": {"name": stored_data_name}},
            "parameters": {"srs": "EPSG:4326"},
        }
        resp = self.session.post(self._url("processings/executions"), json=payload)
        self._raise(resp)
        exec_id = resp.json()["_id"]

        resp = self.session.post(self._url(f"processings/executions/{exec_id}/launch"))
        self._raise(resp)
        return exec_id

    def poll_execution(self, exec_id):
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

    def tag_entity(self, entity_type, entity_id, datasheet_name):
        # entity_type: "uploads", "stored_data", "metadata"
        resp = self.session.post(
            self._url(f"{entity_type}/{entity_id}/tags"),
            json={"datasheet_name": datasheet_name},
        )
        self._raise(resp)

    # --- offerings ---

    def list_offerings(self, stored_data_id: str) -> list:
        """Return offerings for a stored_data, including urls and type."""
        resp = self.session.get(
            self._url("offerings"),
            params={"stored_data": stored_data_id, "fields": "urls,type,layer_name,status,open"},
        )
        self._raise(resp)
        return resp.json()

    # --- metadata ---

    def upload_metadata(self, xml_bytes):
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
                f"409 on metadata upload, could not locate existing record: {resp.text}"
            )
        self._raise(resp)
        return resp.json()["_id"]

    def _find_metadata_id(self, file_identifier):
        resp = self.session.get(self._url("metadata"))
        self._raise(resp)
        for item in resp.json():
            if item.get("file_identifier") == file_identifier:
                return item["_id"]
        return None

    def update_metadata(self, metadata_id, xml_bytes):
        resp = self.session.put(
            self._url(f"metadata/{metadata_id}"),
            files={"file": ("metadata.xml", io.BytesIO(xml_bytes), "application/xml")},
        )
        self._raise(resp)
        return metadata_id


def _extract_file_identifier(xml_bytes):
    el = fromstring(xml_bytes).find("gmd:fileIdentifier/gco:CharacterString", XML_NS)
    if el is None or not el.text:
        raise GeopfError("Could not extract file_identifier from metadata XML")
    return el.text
