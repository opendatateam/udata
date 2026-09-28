import pytest
from lxml import etree

from udata.harvest.backends.maaf import XML_PARSER, MaafBackend
from udata.harvest.exceptions import HarvestValidationError
from udata.tests.api import PytestOnlyDBTestCase

from .factories import HarvestSourceFactory

MAAF_XML = """<?xml version="1.0" encoding="UTF-8"?>
{doctype}
<ETALAB>
    <metadata>
        <author>Service de publication des données ouvertes</author>
        <author_email/>
        <extras>
            <key>Quartier</key>
            <value>SIAL</value>
        </extras>
        <frequency>annuelle</frequency>
        <groups/>
        <id>MINAGRI-SIAL-EPHY-Test</id>
        <license_id>fr-lo</license_id>
        <maintainer/>
        <maintainer_email/>
        <notes>{notes}</notes>
        <organization>Ministère de l’Agriculture</organization>
        <private>0</private>
        <resources>
            <description>Données brutes</description>
            <format>csv</format>
            <name>Test</name>
            <url>https://fichiers-publics.agriculture.gouv.fr/etalab/test.csv</url>
        </resources>
        <state>active</state>
        <supplier>Ministère de l’Agriculture</supplier>
        <tags>test</tags>
        <temporal_coverage_from/>
        <temporal_coverage_to/>
        <territorial_coverage>
            <territorial_coverage_code>country/fr</territorial_coverage_code>
            <territorial_coverage_granularity>france</territorial_coverage_granularity>
        </territorial_coverage>
        <title>Test</title>
    </metadata>
</ETALAB>
"""

SECRET = "s3cr3t-content-that-must-not-leak"


def build_xml(doctype="", notes="A description"):
    """Build a MAAF descriptor as bytes, the way the backend receives it over HTTP."""
    return MAAF_XML.format(doctype=doctype, notes=notes).encode("utf-8")


@pytest.fixture
def secret_file(tmp_path):
    path = tmp_path / "secret.txt"
    path.write_text(SECRET)
    return path


@pytest.fixture
def exfiltrating_dtd(tmp_path, secret_file):
    """A DTD wrapping a local file into a general entity, the second stage of an XXE.

    The attacker plants it on the server filesystem (e.g. as a community resource) so
    that it can be referenced with `file://`, since the parser refuses network access.
    """
    path = tmp_path / "payload.dtd"
    path.write_text(
        f'<!ENTITY % target SYSTEM "file://{secret_file}">\n'
        "<!ENTITY % wrapper \"<!ENTITY leak '%target;'>\">\n"
        "%wrapper;\n"
    )
    return path


class MaafBackendTest(PytestOnlyDBTestCase):
    def test_parse_xml(self):
        metadata = MaafBackend(HarvestSourceFactory()).parse_xml(build_xml())["metadata"]

        assert metadata["notes"] == "A description"
        assert metadata["id"] == "MINAGRI-SIAL-EPHY-Test"

    def test_parse_xml_rejects_dtd(self, exfiltrating_dtd):
        """A harvested descriptor must not be able to read the server filesystem."""
        backend = MaafBackend(HarvestSourceFactory())
        doctype = (
            f'<!DOCTYPE ETALAB [\n  <!ENTITY % remote SYSTEM "file://{exfiltrating_dtd}">\n'
            "  %remote;\n]>"
        )

        with pytest.raises(HarvestValidationError) as excinfo:
            backend.parse_xml(build_xml(doctype=doctype, notes="&leak;"))

        assert SECRET not in str(excinfo.value)


class XmlParserTest:
    """The hardened parser is the actual guard: it holds even without the DTD check.

    lxml's default parser blocks general external entities but not parameter entities
    declared in the internal subset, which are enough to smuggle a local file in.
    """

    def test_does_not_resolve_external_general_entity(self, secret_file):
        xml = (
            f'<!DOCTYPE root [<!ENTITY leak SYSTEM "file://{secret_file}">]><root>&leak;</root>'
        ).encode("utf-8")

        root = etree.fromstring(xml, parser=XML_PARSER)

        assert SECRET not in etree.tostring(root, encoding="unicode")

    def test_does_not_resolve_external_parameter_entity(self, exfiltrating_dtd):
        xml = (
            f'<!DOCTYPE root [<!ENTITY % remote SYSTEM "file://{exfiltrating_dtd}"> %remote;]>'
            "<root>&leak;</root>"
        ).encode("utf-8")

        root = etree.fromstring(xml, parser=XML_PARSER)

        assert SECRET not in etree.tostring(root, encoding="unicode")
