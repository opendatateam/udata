import pytest
from flask import url_for
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import FOAF, RDF
from rdflib.resource import Resource

from udata.core.dataservices.factories import DataserviceFactory, HarvestMetadataFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.site.factories import SiteFactory
from udata.core.site.rdf import build_catalog
from udata.core.user.factories import UserFactory
from udata.rdf import CONTEXT, DCAT, DCT, HYDRA
from udata.tests.helpers import assert200, assert404, assert_redirects

pytestmark = pytest.mark.usefixtures("clean_db")


@pytest.mark.frontend
class CatalogTest:
    def test_minimal(self, app):
        site = SiteFactory()
        home_url = url_for("api.site", _external=True)
        uri = url_for("api.site_rdf_catalog", _external=True)
        datasets = DatasetFactory.create_batch(3)
        catalog = build_catalog(site, datasets)
        graph = catalog.graph

        assert isinstance(catalog, Resource)
        catalogs = graph.subjects(RDF.type, DCAT.Catalog)
        assert len(list(catalogs)) == 1

        assert catalog.value(RDF.type).identifier == DCAT.Catalog

        assert isinstance(catalog.identifier, URIRef)
        assert str(catalog.identifier) == uri
        assert catalog.value(DCT.title) == Literal(site.title)
        assert catalog.value(DCT.description) == Literal(f"{site.title}")
        lang = app.config["DEFAULT_LANGUAGE"]
        assert catalog.value(DCT.language) == Literal(lang)

        assert len(list(catalog.objects(DCAT.dataset))) == len(datasets)

        assert catalog.value(FOAF.homepage).identifier == URIRef(home_url)

        org = catalog.value(DCT.publisher)
        assert org.value(RDF.type).identifier == FOAF.Organization
        assert org.value(FOAF.name) == Literal(app.config["SITE_AUTHOR"])

        graph = catalog.graph
        graph_datasets = graph.subjects(RDF.type, DCAT.Dataset)
        assert len(list(graph_datasets)) == len(datasets)

    def test_no_duplicate(self):
        site = SiteFactory()
        org = OrganizationFactory()
        user = UserFactory()
        datasets = DatasetFactory.create_batch(2, owner=user)
        datasets += DatasetFactory.create_batch(2, organization=org)
        catalog = build_catalog(site, datasets)
        graph = catalog.graph

        orgs = list(graph.subjects(RDF.type, FOAF.Organization))
        assert len(orgs) == 1 + 1  # There is the site publisher
        users = list(graph.subjects(RDF.type, FOAF.Person))
        assert len(users) == 1
        org_names = list(graph.objects(orgs[0], FOAF.name))
        assert len(org_names) == 1
        user_names = list(graph.objects(users[0], FOAF.name))
        assert len(user_names) == 1

    def test_pagination(self):
        site = SiteFactory()
        page_size = 3
        total = 4
        uri = url_for("api.site_rdf_catalog", _external=True)
        uri_first = url_for(
            "api.site_rdf_catalog_format",
            format="json",
            page=1,
            page_size=page_size,
            _external=True,
        )
        uri_last = url_for(
            "api.site_rdf_catalog_format",
            format="json",
            page=2,
            page_size=page_size,
            _external=True,
        )
        DatasetFactory.create_batch(total)

        # First page
        datasets = Dataset.objects.paginate(1, page_size)
        catalog = build_catalog(site, datasets, format="json")
        graph = catalog.graph

        assert isinstance(catalog, Resource)
        assert catalog.identifier == URIRef(uri)
        types = [o.identifier for o in catalog.objects(RDF.type)]
        assert DCAT.Catalog in types
        assert HYDRA.Collection in types

        assert catalog.value(HYDRA.totalItems) == Literal(total)

        assert len(list(catalog.objects(DCAT.dataset))) == page_size

        paginations = list(graph.subjects(RDF.type, HYDRA.PartialCollectionView))
        assert len(paginations) == 1
        pagination = graph.resource(paginations[0])
        assert pagination.identifier == URIRef(uri_first)
        assert pagination.value(HYDRA.first).identifier == URIRef(uri_first)
        assert pagination.value(HYDRA.next).identifier == URIRef(uri_last)
        assert pagination.value(HYDRA.last).identifier == URIRef(uri_last)
        assert HYDRA.previous not in pagination

        # Second page
        datasets = Dataset.objects.paginate(2, page_size)
        catalog = build_catalog(site, datasets, format="json")
        graph = catalog.graph

        assert isinstance(catalog, Resource)
        assert catalog.identifier == URIRef(uri)
        types = [o.identifier for o in catalog.objects(RDF.type)]
        assert DCAT.Catalog in types
        assert HYDRA.Collection in types

        assert catalog.value(HYDRA.totalItems) == Literal(total)

        assert len(list(catalog.objects(DCAT.dataset))) == 1

        paginations = list(graph.subjects(RDF.type, HYDRA.PartialCollectionView))
        assert len(paginations) == 1
        pagination = graph.resource(paginations[0])
        assert pagination.identifier == URIRef(uri_last)
        assert pagination.value(HYDRA.first).identifier == URIRef(uri_first)
        assert pagination.value(HYDRA.previous).identifier == URIRef(uri_first)
        assert pagination.value(HYDRA.last).identifier == URIRef(uri_last)
        assert HYDRA.next not in pagination


@pytest.mark.frontend
class SiteRdfViewsTest:
    def test_expose_jsonld_context(self, client):
        url = url_for("api.site_jsonld_context")
        assert url == "/api/1/site/context.jsonld"

        response = client.get(url, headers={"Accept": "application/ld+json"})
        assert200(response)
        assert response.content_type == "application/ld+json"
        assert response.json == CONTEXT

    def test_catalog_default_to_jsonld(self, client):
        expected = url_for("api.site_rdf_catalog_format", format="json")
        response = client.get(url_for("api.site_rdf_catalog"))
        assert_redirects(response, expected)

    def test_rdf_perform_content_negociation(self, client):
        expected = url_for("api.site_rdf_catalog_format", format="xml")
        url = url_for("api.site_rdf_catalog")
        headers = {"accept": "application/xml"}
        response = client.get(url, headers=headers)
        assert_redirects(response, expected)

    @pytest.mark.parametrize("fmt", ("json", "jsonld"))
    def test_catalog_rdf_json_ld(self, fmt, client):
        url = url_for("api.site_rdf_catalog_format", format=fmt)
        response = client.get(url, headers={"Accept": "application/ld+json"})
        assert200(response)
        assert response.content_type == "application/ld+json"
        assert response.json["@context"]["@vocab"] == "http://www.w3.org/ns/dcat#"

    def test_catalog_rdf_n3(self, client):
        url = url_for("api.site_rdf_catalog_format", format="n3")
        response = client.get(url, headers={"Accept": "text/n3"})
        assert200(response)
        assert response.content_type == "text/n3"

    def test_catalog_rdf_turtle(self, client):
        url = url_for("api.site_rdf_catalog_format", format="ttl")
        response = client.get(url, headers={"Accept": "application/x-turtle"})
        assert200(response)
        assert response.content_type == "application/x-turtle"

    @pytest.mark.parametrize("fmt", ("xml", "rdf", "owl"))
    def test_catalog_rdf_rdfxml(self, fmt, client):
        url = url_for("api.site_rdf_catalog_format", format=fmt)
        response = client.get(url, headers={"Accept": "application/rdf+xml"})
        assert200(response)
        assert response.content_type == "application/rdf+xml"

    def test_catalog_rdf_n_triples(self, client):
        url = url_for("api.site_rdf_catalog_format", format="nt")
        response = client.get(url, headers={"Accept": "application/n-triples"})
        assert200(response)
        assert response.content_type == "application/n-triples"

    def test_catalog_rdf_trig(self, client):
        url = url_for("api.site_rdf_catalog_format", format="trig")
        response = client.get(url, headers={"Accept": "application/trig"})
        assert200(response)
        assert response.content_type == "application/trig"

    @pytest.mark.parametrize("fmt", ("json", "xml", "ttl"))
    def test_dataportal_compliance(self, fmt, client):
        url = url_for("api.site_dataportal", format=fmt)
        assert url == "/api/1/site/data.{0}".format(fmt)
        expected_url = url_for("api.site_rdf_catalog_format", format=fmt)

        response = client.get(url)
        assert_redirects(response, expected_url)

    def test_catalog_rdf_paginate(self, client):
        DatasetFactory.create_batch(4)
        url = url_for("api.site_rdf_catalog_format", format="n3", page_size=3)
        next_url = url_for(
            "api.site_rdf_catalog_format", format="n3", page=2, page_size=3, _external=True
        )

        response = client.get(url, headers={"Accept": "text/n3"})
        assert200(response)

        graph = Graph().parse(data=response.data, format="n3")
        pagination = graph.value(predicate=RDF.type, object=HYDRA.PartialCollectionView)
        assert pagination is not None
        pagination = graph.resource(pagination)
        assert not pagination.value(HYDRA.previous)
        assert pagination.value(HYDRA.next).identifier == URIRef(next_url)

    def test_catalog_format_unknown(self, client):
        url = url_for("api.site_rdf_catalog_format", format="unknown")
        response = client.get(url)
        assert404(response)

    def test_catalog_rdf_filter_tag(self, client):
        DatasetFactory.create_batch(4, tags=["my-tag"])
        DatasetFactory.create_batch(3)
        url = url_for("api.site_rdf_catalog_format", format="xml", tag="my-tag")

        response = client.get(url, headers={"Accept": "application/xml"})
        assert200(response)

        graph = Graph().parse(data=response.data, format="xml")

        datasets = list(graph.subjects(RDF.type, DCAT.Dataset))
        assert len(datasets) == 4

        for dat in datasets:
            assert graph.value(dat, DCAT.keyword) == Literal("my-tag")

    def test_catalog_rdf_dataservices(self, client):
        dataset_a = DatasetFactory.create()
        dataset_b = DatasetFactory.create()
        dataset_c = DatasetFactory.create()

        DataserviceFactory.create(datasets=[dataset_a.id], harvest=HarvestMetadataFactory())
        dataservice_b = DataserviceFactory.create(datasets=[dataset_b.id])
        dataservice_x = DataserviceFactory.create(datasets=[dataset_a.id, dataset_c.id])
        dataservice_y = DataserviceFactory.create(datasets=[])

        response = client.get(
            url_for("api.site_rdf_catalog_format", format="xml"),
            headers={"Accept": "application/xml"},
        )
        assert200(response)

        graph = Graph().parse(data=response.data, format="xml")

        datasets = list(graph.subjects(RDF.type, DCAT.Dataset))
        assert len(datasets) == 3

        # 4 objects of RDF.type DCAT.DataService
        dataservices = list(graph.subjects(RDF.type, DCAT.DataService))
        assert len(dataservices) == 4

        # these 4 objects are also bound to catalog by DCAT.service predicate
        catalog = graph.resource(next(graph.subjects(RDF.type, DCAT.Catalog)))
        assert len(list(catalog.objects(DCAT.service))) == 4

        # Test first page contains the dataservice without dataset
        response = client.get(
            url_for("api.site_rdf_catalog_format", format="xml", page_size=1),
            headers={"Accept": "application/xml"},
        )
        assert200(response)

        graph = Graph().parse(data=response.data, format="xml")

        datasets = list(graph.subjects(RDF.type, DCAT.Dataset))
        assert len(datasets) == 1
        assert str(graph.value(datasets[0], DCT.identifier)) == str(dataset_c.id)

        dataservices = list(graph.subjects(RDF.type, DCAT.DataService))
        assert len(dataservices) == 2
        assert sorted([str(d.id) for d in [dataservice_x, dataservice_y]]) == sorted(
            [str(graph.value(d, DCT.identifier)) for d in dataservices]
        )

        # Test second page doesn't contains the dataservice without dataset
        response = client.get(
            url_for("api.site_rdf_catalog_format", format="xml", page_size=1, page=2),
            headers={"Accept": "application/xml"},
        )
        assert200(response)

        graph = Graph().parse(data=response.data, format="xml")

        datasets = list(graph.subjects(RDF.type, DCAT.Dataset))
        assert len(datasets) == 1
        assert str(graph.value(datasets[0], DCT.identifier)) == str(dataset_b.id)

        dataservices = list(graph.subjects(RDF.type, DCAT.DataService))
        assert len(dataservices) == 1
        assert str(graph.value(dataservices[0], DCT.identifier)) == str(dataservice_b.id)
