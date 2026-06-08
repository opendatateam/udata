from xml.etree.ElementTree import fromstring

from udata.core.dataset.factories import DatasetFactory, LicenseFactory
from udata.geopf.metadata import FRANCE_METRO_BBOX, dataset_to_iso19115
from udata.tests.api import PytestOnlyDBTestCase

NS = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
}


def _text(root, xpath):
    el = root.find(xpath, NS)
    return el.text if el is not None else None


def _parse(dataset):
    return fromstring(dataset_to_iso19115(dataset))


class DatasetToIso19115Test(PytestOnlyDBTestCase):
    def test_file_identifier(self):
        dataset = DatasetFactory.build()
        root = _parse(dataset)
        fid = _text(root, ".//gmd:fileIdentifier/gco:CharacterString")
        assert fid == str(dataset.id)

    def test_title_and_abstract(self):
        dataset = DatasetFactory.build(title="My Dataset", description="Desc")
        root = _parse(dataset)
        title = _text(
            root, ".//gmd:identificationInfo//gmd:citation//gmd:title/gco:CharacterString"
        )
        abstract = _text(root, ".//gmd:identificationInfo//gmd:abstract/gco:CharacterString")
        assert title == "My Dataset"
        assert abstract == "Desc"

    def test_abstract_fallback_to_title(self):
        dataset = DatasetFactory.build(title="My Title", description=None)
        root = _parse(dataset)
        abstract = _text(root, ".//gmd:identificationInfo//gmd:abstract/gco:CharacterString")
        assert abstract == "My Title"

    def test_france_metro_bbox_default(self):
        dataset = DatasetFactory.build(spatial=None)
        root = _parse(dataset)
        west = _text(root, ".//gmd:westBoundLongitude/gco:Decimal")
        assert west == str(FRANCE_METRO_BBOX[0])

    def test_license_url_in_constraints(self):
        license = LicenseFactory.build(url="https://example.org/license")
        dataset = DatasetFactory.build(license=license)
        root = _parse(dataset)
        constraints = _text(
            root, ".//gmd:resourceConstraints//gmd:otherConstraints/gco:CharacterString"
        )
        assert constraints == "https://example.org/license"

    def test_keywords_from_tags(self):
        dataset = DatasetFactory.build(tags=["geo", "france"])
        root = _parse(dataset)
        keywords = [
            el.text
            for el in root.findall(
                ".//gmd:descriptiveKeywords//gmd:keyword/gco:CharacterString", NS
            )
        ]
        assert "geo" in keywords
        assert "france" in keywords

    def test_xml_is_valid_bytes(self):
        dataset = DatasetFactory.build()
        result = dataset_to_iso19115(dataset)
        assert isinstance(result, bytes)
        assert result.startswith(b"<?xml")
