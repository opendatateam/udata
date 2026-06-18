"""
End-to-end CSW harvest tests against real CSW servers (PyCSW and GeoNetwork)
running as CI service containers.

Unlike the mocked tests in `test_dcat_backend.py`, these run the whole harvest
pipeline against a server's own request parser — the only thing that can catch
a request that is valid XML but rejected by a real catalog.

Context: PR #3837 capitalized the `apiso:` property names (`apiso:type` ->
`apiso:Type`, `apiso:identifier` -> `apiso:Identifier`) to satisfy a PyCSW
instance. These tests reproduce, end to end, what each server family does with
the *current* code: PyCSW is expected to accept the request, while GeoNetwork
is expected to reject the capitalized request (the GeoIDE failure mode), which
makes the harvest fail with a "Failed to query CSW" error.

The GeoNetwork record is pushed over its REST API at the start of the test (no
records need to be loaded into PyCSW: a request parse error happens before any
data lookup). Skipped unless `UDATA_TEST_CSW_INTEGRATION=1` and both servers
are reachable, so they only run in the dedicated CI job.
"""

import os
from pathlib import Path

import pytest
import requests

from udata.core.organization.factories import OrganizationFactory
from udata.models import Dataset
from udata.tests.api import PytestOnlyDBTestCase

from .. import actions
from .factories import HarvestSourceFactory

pytestmark = pytest.mark.skipif(
    not os.environ.get("UDATA_TEST_CSW_INTEGRATION"),
    reason="Set UDATA_TEST_CSW_INTEGRATION=1 to run CSW integration tests against real servers",
)

PYCSW_URL = os.environ.get("CSW_PYCSW_URL", "http://localhost:8000/")
GEONETWORK_URL = os.environ.get(
    "CSW_GEONETWORK_URL", "http://localhost:8080/geonetwork/srv/eng/csw"
)
GEONETWORK_BASE = os.environ.get("CSW_GEONETWORK_BASE", "http://localhost:8080/geonetwork")

RECORD = Path(__file__).parent / "csw_dcat" / "records" / "combles.xml"
# Title produced by harvesting `records/combles.xml` (same record and mapping
# as `test_geoide` in test_dcat_backend.py).
EXPECTED_TITLE = "Plan local d'urbanisme de la commune de Combles"

QUERY_REJECTED = "Failed to query CSW"


def load_geonetwork_record():
    """Push the ISO-19139 test record into GeoNetwork and publish it.

    GeoNetwork requires an XSRF token (set as a cookie on a first authenticated
    call) to be echoed back as a header on the insert request.
    """
    session = requests.Session()
    session.auth = ("admin", "admin")

    session.get(f"{GEONETWORK_BASE}/srv/api/me", timeout=30)
    token = session.cookies.get("XSRF-TOKEN")

    response = session.put(
        f"{GEONETWORK_BASE}/srv/api/records",
        params={
            "metadataType": "METADATA",
            "uuidProcessing": "OVERWRITE",
            "group": "2",
            "rejectIfInvalid": "false",
            "publishToAll": "true",
        },
        headers={
            "X-XSRF-TOKEN": token,
            "Content-Type": "application/xml",
            "Accept": "application/json",
        },
        data=RECORD.read_bytes(),
        timeout=30,
    )
    response.raise_for_status()


@pytest.mark.options(HARVESTER_BACKENDS=["csw*"])
class CswIntegrationTest(PytestOnlyDBTestCase):
    def harvest(self, url):
        source = HarvestSourceFactory(
            backend="csw-iso-19139",
            url=url,
            organization=OrganizationFactory(),
        )
        actions.run(source)
        source.reload()
        return source.get_last_job()

    def test_pycsw_accepts_request(self):
        """PyCSW must parse our GetRecords request (the casing it was tuned for).

        We only assert the request was accepted, not on specific datasets: the
        stock PyCSW image is preloaded with unrelated conformance data, so its
        records may or may not convert cleanly — that is not what we test here.
        """
        job = self.harvest(PYCSW_URL)

        query_errors = [error.message for error in job.errors if QUERY_REJECTED in error.message]
        assert not query_errors, query_errors

    def test_geonetwork_harvests_record(self):
        """GeoNetwork must accept the request and yield the published record.

        On the current (capitalized) code this fails: GeoNetwork rejects the
        request with a "Failed to query CSW" error — the GeoIDE bug, reproduced.
        """
        load_geonetwork_record()

        job = self.harvest(GEONETWORK_URL)

        query_errors = [error.message for error in job.errors if QUERY_REJECTED in error.message]
        assert not query_errors, query_errors

        titles = {dataset.title for dataset in Dataset.objects}
        assert EXPECTED_TITLE in titles, titles
