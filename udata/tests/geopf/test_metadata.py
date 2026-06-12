from xml.etree.ElementTree import fromstring

import pytest

from udata.core.contact_point.factories import ContactPointFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.spatial.models import SpatialCoverage
from udata.core.user.factories import UserFactory
from udata.geopf.metadata import XML_NS, dataset_to_iso19115
from udata.tests.api import PytestOnlyDBTestCase


def _text(root, xpath):
    el = root.find(xpath, XML_NS)
    return el.text if el is not None else None


def _decimal(root, xpath):
    el = root.find(xpath, XML_NS)
    return float(el.text) if el is not None else None


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

    def test_extent_omitted_when_no_geom(self):
        dataset = DatasetFactory.build(spatial=None)
        root = _parse(dataset)
        assert root.find(".//gmd:extent", XML_NS) is None

    def test_keywords_from_tags(self):
        dataset = DatasetFactory.build(tags=["geo", "france"])
        root = _parse(dataset)
        keywords = [
            el.text
            for el in root.findall(
                ".//gmd:descriptiveKeywords//gmd:keyword/gco:CharacterString", XML_NS
            )
        ]
        assert "geo" in keywords
        assert "france" in keywords

    def test_xml_is_valid_bytes(self):
        dataset = DatasetFactory.build()
        result = dataset_to_iso19115(dataset)
        assert isinstance(result, bytes)
        assert result.startswith(b"<?xml")

    def test_contact_email_from_contact_points(self):
        cp = ContactPointFactory(email="geo@example.com")
        dataset = DatasetFactory(org=True, contact_points=[cp])
        root = _parse(dataset)
        emails = [
            el.text
            for el in root.findall(".//gmd:electronicMailAddress/gco:CharacterString", XML_NS)
        ]
        # email appears in top-level gmd:contact AND gmd:pointOfContact inside identificationInfo
        assert emails.count("geo@example.com") == 2

    def test_no_contact_email_when_no_contact_points(self):
        dataset = DatasetFactory.build(contact_points=[])
        root = _parse(dataset)
        assert root.find(".//gmd:electronicMailAddress", XML_NS) is None

    def test_point_of_contact_org_name(self):
        dataset = DatasetFactory(org=True)
        root = _parse(dataset)
        org = _text(
            root,
            ".//gmd:identificationInfo//gmd:pointOfContact//gmd:organisationName/gco:CharacterString",
        )
        assert org

    def test_topic_category_matched_from_tags(self):
        dataset = DatasetFactory.build(tags=["unrelated", "transport", "other"])
        root = _parse(dataset)
        topic = _text(root, ".//gmd:topicCategory/gmd:MD_TopicCategoryCode")
        assert topic == "transportation"

    def test_topic_category_absent_when_no_match(self):
        dataset = DatasetFactory.build(tags=["random-tag-xyz"])
        root = _parse(dataset)
        assert root.find(".//gmd:topicCategory", XML_NS) is None

    @pytest.mark.parametrize(
        "tag,expected",
        [
            ("agriculture", "farming"),
            ("environnement", "environment"),
            ("eau", "inlandWaters"),
            ("cadastre", "planningCadastre"),
            ("sante", "health"),
            ("elevation", "elevation"),
        ],
    )
    def test_topic_category_mapping_samples(self, tag, expected):
        dataset = DatasetFactory.build(tags=[tag])
        root = _parse(dataset)
        topic = _text(root, ".//gmd:topicCategory/gmd:MD_TopicCategoryCode")
        assert topic == expected

    def test_no_keywords_block_when_no_tags(self):
        dataset = DatasetFactory.build(tags=[])
        root = _parse(dataset)
        assert root.find(".//gmd:descriptiveKeywords", XML_NS) is None

    def test_extent_values_from_geom(self):
        geom = {
            "type": "MultiPolygon",
            "coordinates": [[[[2.0, 48.0], [3.0, 48.0], [3.0, 49.0], [2.0, 49.0], [2.0, 48.0]]]],
        }
        dataset = DatasetFactory.build(spatial=SpatialCoverage(geom=geom))
        root = _parse(dataset)
        assert _decimal(root, ".//gmd:westBoundLongitude/gco:Decimal") == 2.0
        assert _decimal(root, ".//gmd:eastBoundLongitude/gco:Decimal") == 3.0
        assert _decimal(root, ".//gmd:southBoundLatitude/gco:Decimal") == 48.0
        assert _decimal(root, ".//gmd:northBoundLatitude/gco:Decimal") == 49.0

    def test_extent_omitted_when_spatial_has_no_geom(self):
        dataset = DatasetFactory.build(spatial=SpatialCoverage())
        root = _parse(dataset)
        assert root.find(".//gmd:extent", XML_NS) is None

    def test_org_name_from_owner_when_no_organization(self):
        user = UserFactory(first_name="Alice", last_name="Martin")
        dataset = DatasetFactory(owner=user)
        root = _parse(dataset)
        org = _text(root, ".//gmd:contact//gmd:organisationName/gco:CharacterString")
        assert org == "Alice Martin"

    def test_no_contact_email_when_contact_point_has_no_email(self):
        cp = ContactPointFactory(email=None)
        dataset = DatasetFactory(org=True, contact_points=[cp])
        root = _parse(dataset)
        assert root.find(".//gmd:electronicMailAddress", XML_NS) is None

    def test_special_characters_escaped_in_title_and_abstract(self):
        dataset = DatasetFactory.build(
            title='Data & <More> "Info"', description="See <https://example.com> & more"
        )
        result = dataset_to_iso19115(dataset)
        assert b"Data &amp; &lt;More&gt;" in result
        assert b"See &lt;https://example.com&gt; &amp; more" in result
