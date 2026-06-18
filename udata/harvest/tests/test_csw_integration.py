"""
End-to-end CSW harvest tests against real CSW servers (PyCSW and GeoNetwork)
running as CI service containers.

Unlike the mocked tests in `test_dcat_backend.py`, these run the whole harvest
pipeline against a server's own request parser — the only thing that can catch
a request that is valid XML but rejected by a real catalog.

Context: PR #3837 capitalized the `apiso:` property names (`apiso:type` ->
`apiso:Type`, `apiso:identifier` -> `apiso:Identifier`) to satisfy a PyCSW
instance, which was reported to break GeoIDE harvests. These tests show that
both servers we can containerize accept the capitalized request: PyCSW (it was
tuned for it) and upstream GeoNetwork (which is lenient about Filter/SortBy
field names, see note [4] in dcat.py). The GeoIDE rejection is specific to
GeoSource, an old GeoNetwork fork that is not containerizable — so it cannot be
reproduced here.

The GeoNetwork record is pushed over CSW-T at the start of the test; PyCSW
serves its built-in conformance data, so it needs no loading. Skipped unless
`UDATA_TEST_CSW_INTEGRATION=1` and both servers are reachable, so they only run
in the dedicated CI job.
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
# Harvest as admin (credentials in the URL) so GeoNetwork returns the freshly
# inserted record, which is not published to the anonymous group by default.
GEONETWORK_AUTH_URL = os.environ.get(
    "CSW_GEONETWORK_AUTH_URL", "http://admin:admin@localhost:8080/geonetwork/srv/eng/csw"
)

RECORD = Path(__file__).parent / "csw_dcat" / "records" / "combles.xml"
# Title produced by harvesting `records/combles.xml` (same record and mapping
# as `test_geoide` in test_dcat_backend.py).
EXPECTED_TITLE = "Plan local d'urbanisme de la commune de Combles"

QUERY_REJECTED = "Failed to query CSW"


def load_geonetwork_record():
    """Push the ISO-19139 test record into GeoNetwork via CSW-T and publish it.

    We use the OGC CSW transaction endpoint (`/srv/eng/csw-publication`) rather
    than the REST API: it goes through the same CSW servlet as the (working)
    harvest endpoint and is not XSRF-protected, only basic-auth.
    """
    record = RECORD.read_text(encoding="utf-8")
    # Drop the XML declaration so the record can be embedded in the transaction.
    if record.lstrip().startswith("<?xml"):
        record = record.split("?>", 1)[1]

    transaction = (
        '<csw:Transaction xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"'
        ' service="CSW" version="2.0.2"><csw:Insert>'
        f"{record}"
        "</csw:Insert></csw:Transaction>"
    )

    response = requests.post(
        f"{GEONETWORK_BASE}/srv/eng/csw-publication",
        data=transaction.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
        auth=("admin", "admin"),
        timeout=60,
    )
    assert response.ok, (
        f"GeoNetwork CSW-T insert failed {response.status_code}: {response.text[:1000]}"
    )
    assert "ExceptionReport" not in response.text, response.text[:1000]


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

    def test_geonetwork_accepts_request(self):
        """Upstream GeoNetwork must parse our GetRecords request.

        Independent of record loading: a parse error would happen before any
        data lookup. Upstream GeoNetwork is lenient and accepts the capitalized
        request — unlike GeoSource/GeoIDE, which is not containerizable here.
        """
        job = self.harvest(GEONETWORK_URL)

        query_errors = [error.message for error in job.errors if QUERY_REJECTED in error.message]
        assert not query_errors, query_errors

    def test_geonetwork_harvests_record(self):
        """Full pipeline: push a record into GeoNetwork, harvest it back out."""
        load_geonetwork_record()

        job = self.harvest(GEONETWORK_AUTH_URL)

        query_errors = [error.message for error in job.errors if QUERY_REJECTED in error.message]
        assert not query_errors, query_errors

        titles = {dataset.title for dataset in Dataset.objects}
        assert EXPECTED_TITLE in titles, titles
