from xml.etree.ElementTree import XML

import pytest
from flask import url_for
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import RDF
from rdflib.resource import Resource as RdfResource

from udata.core.constants import HVD
from udata.core.dataservices.factories import DataserviceFactory, HarvestMetadataFactory
from udata.core.dataservices.rdf import dataservice_to_rdf
from udata.core.dataset.factories import DatasetFactory
from udata.rdf import (
    DCAT,
    DCATAP,
    DCT,
    HVD_LEGISLATION,
    TAG_TO_EU_HVD_CATEGORIES,
)
from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import assert200, assert_redirects


class DataserviceToRdfTest(PytestOnlyAPITestCase):
    def test_minimal(self):
        dataservice = DataserviceFactory.build()  # Does not have an URL
        d = dataservice_to_rdf(dataservice)
        g = d.graph

        assert isinstance(d, RdfResource)

        assert g.value(d.identifier, RDF.type) == DCAT.DataService

        assert isinstance(d.identifier, BNode)
        assert d.value(DCT.identifier) == Literal(dataservice.id)
        assert d.value(DCT.title) == Literal(dataservice.title)

        # no harvest extras, fallback to internal values for dates
        assert d.value(DCT.created) == Literal(dataservice.created_at)
        assert d.value(DCT.issued) == Literal(dataservice.created_at)
        assert d.value(DCT.modified) == Literal(dataservice.metadata_modified_at)

    def test_harvested_dates(self):
        dataservice = DataserviceFactory(harvest=HarvestMetadataFactory())
        d = dataservice_to_rdf(dataservice)
        assert d.value(DCT.created) == Literal(dataservice.harvest.created_at)
        assert d.value(DCT.issued) == Literal(dataservice.harvest.issued_at)
        assert d.value(DCT.modified) == Literal(dataservice.metadata_modified_at)

    def test_hvd_dataservice(self):
        """Test that a dataservice tagged hvd has appropriate DCAT-AP HVD properties"""
        dataservice = DataserviceFactory(tags=["hvd", "mobilite", "test"])
        dataservice.add_badge(HVD)
        d = dataservice_to_rdf(dataservice)

        assert d.value(DCATAP.applicableLegislation).identifier == URIRef(HVD_LEGISLATION)
        assert d.value(DCATAP.hvdCategory).identifier == URIRef(
            TAG_TO_EU_HVD_CATEGORIES["mobilite"]
        )
        for distrib in d.objects(DCAT.distribution):
            assert distrib.value(DCATAP.applicableLegislation).identifier == URIRef(HVD_LEGISLATION)

    def test_hvd_dataservice_with_hvd_datasets(self):
        """Test that a dataservice tagged hvd has its datasets' HVD categories"""
        dataset = DatasetFactory(tags=["meteorologiques"])
        dataset_hvd_1 = DatasetFactory(tags=["hvd", "statistiques", "not-a-hvd-category"])
        dataset_hvd_2 = DatasetFactory(
            tags=["hvd", "statistiques", "mobilite", "geospatiales", "not-a-hvd-category"]
        )
        dataset_hvd_1.add_badge(HVD)
        dataset_hvd_2.add_badge(HVD)
        dataservice = DataserviceFactory(
            datasets=[dataset, dataset_hvd_1, dataset_hvd_2], tags=["hvd", "mobilite", "test"]
        )
        dataservice.add_badge(HVD)
        d = dataservice_to_rdf(dataservice)

        assert d.value(DCATAP.applicableLegislation).identifier == URIRef(HVD_LEGISLATION)
        hvd_categories = [cat.identifier for cat in d.objects(DCATAP.hvdCategory)]
        assert len(hvd_categories) == 3
        assert URIRef(TAG_TO_EU_HVD_CATEGORIES["mobilite"]) in hvd_categories
        assert URIRef(TAG_TO_EU_HVD_CATEGORIES["geospatiales"]) in hvd_categories
        assert URIRef(TAG_TO_EU_HVD_CATEGORIES["statistiques"]) in hvd_categories
        assert URIRef(TAG_TO_EU_HVD_CATEGORIES["meteorologiques"]) not in hvd_categories
        for distrib in d.objects(DCAT.distribution):
            assert distrib.value(DCATAP.applicableLegislation).identifier == URIRef(HVD_LEGISLATION)


class DataserviceRdfViewsTest(PytestOnlyAPITestCase):
    def test_rdf_default_to_jsonld(self, client):
        dataservice = DataserviceFactory()
        expected = url_for("api.dataservice_rdf_format", dataservice=dataservice.id, _format="json")
        response = client.get(url_for("api.dataservice_rdf", dataservice=dataservice))
        assert_redirects(response, expected)

    def test_rdf_perform_content_negociation(self, client):
        dataservice = DataserviceFactory()
        expected = url_for("api.dataservice_rdf_format", dataservice=dataservice.id, _format="xml")
        url = url_for("api.dataservice_rdf", dataservice=dataservice)
        headers = {"accept": "application/xml"}
        response = client.get(url, headers=headers)
        assert_redirects(response, expected)

    def test_rdf_perform_content_negociation_response(self, client):
        """Check we have valid XML as output"""
        dataservice = DataserviceFactory()
        url = url_for("api.dataservice_rdf", dataservice=dataservice)
        headers = {"accept": "application/xml"}
        response = client.get(url, headers=headers, follow_redirects=True)
        element = XML(response.data)
        assert element.tag == "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"

    def test_dataservice_rdf_json_ld(self, client):
        dataservice = DataserviceFactory()
        for fmt in "json", "jsonld":
            url = url_for("api.dataservice_rdf_format", dataservice=dataservice, _format=fmt)
            response = client.get(url, headers={"Accept": "application/ld+json"})
            assert200(response)
            assert response.content_type == "application/ld+json"
            assert response.json["@context"]["@vocab"] == "http://www.w3.org/ns/dcat#"

    @pytest.mark.parametrize(
        "fmt,mime",
        [
            ("n3", "text/n3"),
            ("nt", "application/n-triples"),
            ("ttl", "application/x-turtle"),
            ("xml", "application/rdf+xml"),
            ("rdf", "application/rdf+xml"),
            ("owl", "application/rdf+xml"),
            ("trig", "application/trig"),
        ],
    )
    def test_dataservice_rdf_formats(self, client, fmt, mime):
        dataservice = DataserviceFactory()
        url = url_for("api.dataservice_rdf_format", dataservice=dataservice, _format=fmt)
        response = client.get(url, headers={"Accept": mime})
        assert200(response)
        assert response.content_type == mime
