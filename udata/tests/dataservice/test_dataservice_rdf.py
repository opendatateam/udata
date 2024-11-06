import pytest
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import RDF
from rdflib.resource import Resource as RdfResource

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.rdf import dataservice_to_rdf
from udata.rdf import (
    DCAT,
    DCATAP,
    DCT,
    HVD_LEGISLATION,
    TAG_TO_EU_HVD_CATEGORIES,
)

pytestmark = pytest.mark.usefixtures("app")


@pytest.mark.frontend
class DataserviceToRdfTest:
    def test_minimal(self):
        dataservice = DataserviceFactory.build()  # Does not have an URL
        d = dataservice_to_rdf(dataservice)
        g = d.graph

        assert isinstance(d, RdfResource)

        assert g.value(d.identifier, RDF.type) == DCAT.DataService

        assert isinstance(d.identifier, BNode)
        assert d.value(DCT.identifier) == Literal(dataservice.id)
        assert d.value(DCT.title) == Literal(dataservice.title)
        assert d.value(DCT.issued) == Literal(dataservice.created_at)

    def test_hvd_dataservice(self):
        """Test that a dataservice tagged hvd has appropriate DCAT-AP HVD properties"""
        dataservice = DataserviceFactory(tags=["hvd", "mobilite", "test"])
        d = dataservice_to_rdf(dataservice)

        assert d.value(DCATAP.applicableLegislation).identifier == URIRef(HVD_LEGISLATION)
        assert d.value(DCATAP.hvdCategory).identifier == URIRef(
            TAG_TO_EU_HVD_CATEGORIES["mobilite"]
        )
        for distrib in d.objects(DCAT.distribution):
            assert distrib.value(DCATAP.applicableLegislation).identifier == URIRef(HVD_LEGISLATION)

    def test_dataservice_with_hvd_datasets(self):
        """Test that a dataservice that serves a dataset tagged hvd has appropriate DCAT-AP HVD properties"""
        pass
