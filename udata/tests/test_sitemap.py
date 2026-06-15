from unittest.mock import patch
from xml.etree import ElementTree

import pytest
from flask import current_app

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.post.factories import PostFactory
from udata.core.reuse.factories import VisibleReuseFactory
from udata.core.topic.factories import TopicFactory
from udata.tests.api import PytestOnlyDBTestCase

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def parse_xml(bytes):
    return ElementTree.fromstring(bytes.decode("utf-8"))


@pytest.mark.options(CDATA_BASE_URL="https://data.gouv.fr")
@pytest.mark.options(SITEMAP_BASE_URL="https://data.gouv.fr")
class SitemapGeneratorTest(PytestOnlyDBTestCase):
    def _generate(self, **config):
        uploaded = {}

        def fake_store_bytes(bucket, filename, bytes, **kwargs):
            uploaded[filename] = bytes

        with patch("udata.core.sitemap.generator.store_bytes", side_effect=fake_store_bytes):
            from udata.core.sitemap.generator import generate_sitemaps

            current_app.config.setdefault("SITEMAP_S3_BUCKET", "test-bucket")
            current_app.config.update(config)
            result = generate_sitemaps()

        return result, uploaded

    @pytest.mark.options(SITEMAP_S3_BUCKET=None)
    def test_skip_when_no_bucket(self):
        result, uploaded = self._generate()
        assert result is False
        assert len(uploaded) == 0

    def test_all_entity_types_included(self):
        DatasetFactory()
        OrganizationFactory()
        VisibleReuseFactory()
        PostFactory()
        DataserviceFactory()
        TopicFactory()

        result, uploaded = self._generate()

        assert result is True
        for name in ("datasets", "organizations", "reuses", "posts", "dataservices", "topics"):
            root = parse_xml(uploaded[f"sitemaps/{name}_1.xml"])
            assert root.tag == f"{{{SITEMAP_NS}}}urlset"
            assert len(root) >= 1

        root = parse_xml(uploaded["sitemaps/sitemap.xml"])
        assert root.tag == f"{{{SITEMAP_NS}}}sitemapindex"
        assert len(root) == 6

    def test_excludes_invisible_entities(self):
        DatasetFactory(private=True)
        DatasetFactory(deleted="2024-01-01")
        DatasetFactory(archived="2024-01-01")
        DatasetFactory()

        OrganizationFactory(deleted="2024-01-01")
        OrganizationFactory()

        VisibleReuseFactory(private=True)
        VisibleReuseFactory(deleted="2024-01-01")
        VisibleReuseFactory()

        DataserviceFactory(private=True)
        DataserviceFactory(deleted_at="2024-01-01")
        DataserviceFactory(archived_at="2024-01-01")
        DataserviceFactory()

        result, uploaded = self._generate()

        assert result is True
        # VisibleReuseFactory creates a DatasetFactory() each time, adding 3
        # extra visible datasets as a side effect.
        assert len(parse_xml(uploaded["sitemaps/datasets_1.xml"])) == 4
        assert len(parse_xml(uploaded["sitemaps/organizations_1.xml"])) == 1
        assert len(parse_xml(uploaded["sitemaps/reuses_1.xml"])) == 1
        assert len(parse_xml(uploaded["sitemaps/dataservices_1.xml"])) == 1

    @pytest.mark.options(SITEMAP_URLS_PER_FILE=2)
    def test_chunking(self):
        DatasetFactory.create_batch(3)

        result, uploaded = self._generate()

        assert result is True
        assert len(parse_xml(uploaded["sitemaps/datasets_1.xml"])) == 2
        assert len(parse_xml(uploaded["sitemaps/datasets_2.xml"])) == 1
        assert len(parse_xml(uploaded["sitemaps/sitemap.xml"])) == 2

    @pytest.mark.options(SITEMAP_URLS_PER_FILE=2)
    def test_multiple_paginated_sitemaps(self):
        DatasetFactory.create_batch(5)
        OrganizationFactory.create_batch(4)

        result, uploaded = self._generate()

        assert result is True

        # datasets: 5 URLs → 3 files (2 + 2 + 1)
        assert len(parse_xml(uploaded["sitemaps/datasets_1.xml"])) == 2
        assert len(parse_xml(uploaded["sitemaps/datasets_2.xml"])) == 2
        assert len(parse_xml(uploaded["sitemaps/datasets_3.xml"])) == 1

        # organizations: 4 URLs → 2 files (2 + 2)
        assert len(parse_xml(uploaded["sitemaps/organizations_1.xml"])) == 2
        assert len(parse_xml(uploaded["sitemaps/organizations_2.xml"])) == 2

        # sitemap index should reference all 5 chunk files
        index = parse_xml(uploaded["sitemaps/sitemap.xml"])
        assert len(index) == 5
        locs = [e.find(f"{{{SITEMAP_NS}}}loc").text for e in index]
        assert any("datasets_3.xml" in loc for loc in locs)
        assert any("organizations_2.xml" in loc for loc in locs)

    def test_each_url_has_loc_and_lastmod(self):
        dataset = DatasetFactory()

        result, uploaded = self._generate()

        assert result is True
        url_elem = parse_xml(uploaded["sitemaps/datasets_1.xml"])[0]
        assert url_elem.find(f"{{{SITEMAP_NS}}}loc").text == dataset.self_web_url()
        assert url_elem.find(f"{{{SITEMAP_NS}}}lastmod").text

    @pytest.mark.options(SITEMAP_S3_PREFIX="custom")
    def test_custom_prefix(self):
        DatasetFactory()

        result, uploaded = self._generate()

        assert result is True
        assert "custom/datasets_1.xml" in uploaded
        assert "custom/sitemap.xml" in uploaded

    def test_index_location_url(self):
        DatasetFactory()

        current_app.config["SITEMAP_BASE_URL"] = "https://data.example.fr"

        result, uploaded = self._generate()

        assert result is True
        loc = parse_xml(uploaded["sitemaps/sitemap.xml"])[0].find(f"{{{SITEMAP_NS}}}loc")
        assert loc.text == "https://data.example.fr/sitemaps/datasets_1.xml"

    def test_sitemap_xml_proper_declaration(self):
        DatasetFactory()

        result, uploaded = self._generate()

        assert result is True
        assert (
            uploaded["sitemaps/datasets_1.xml"]
            .decode("utf-8")
            .startswith('<?xml version="1.0" encoding="UTF-8"?>')
        )
