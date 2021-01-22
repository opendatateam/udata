from flask import url_for

from rdflib import URIRef, Literal, BNode
from rdflib.namespace import RDF, FOAF, RDFS
from rdflib.resource import Resource as RdfResource

from udata.rdf import CONTEXT, DCAT, DCT, HYDRA
from udata.tests import TestCase, DBTestMixin
from udata.core.dataset.views import blueprint as dataset_blueprint
from udata.core.organization.views import blueprint as org_blueprint
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.rdf import organization_to_rdf, build_org_catalog
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.dataset.models import Dataset
from udata.utils import faker


class OrganizationToRdfTest(DBTestMixin, TestCase):
    def create_app(self):
        app = super(OrganizationToRdfTest, self).create_app()
        app.register_blueprint(org_blueprint)
        app.register_blueprint(dataset_blueprint)
        return app

    def test_minimal(self):
        org = OrganizationFactory.build()  # Does not have an URL
        o = organization_to_rdf(org)
        g = o.graph

        self.assertIsInstance(o, RdfResource)
        self.assertEqual(len(list(g.subjects(RDF.type, FOAF.Organization))), 1)

        self.assertEqual(o.value(RDF.type).identifier, FOAF.Organization)

        self.assertIsInstance(o.identifier, BNode)
        self.assertEqual(o.value(FOAF.name), Literal(org.name))
        self.assertEqual(o.value(RDFS.label), Literal(org.name))

    def test_all_fields(self):
        org = OrganizationFactory(url=faker.uri())
        org_url = url_for('organizations.show_redirect',
                          org=org.id,
                          _external=True)
        o = organization_to_rdf(org)
        g = o.graph

        self.assertIsInstance(o, RdfResource)
        self.assertEqual(len(list(g.subjects(RDF.type, FOAF.Organization))), 1)

        self.assertEqual(o.value(RDF.type).identifier, FOAF.Organization)

        self.assertIsInstance(o.identifier, URIRef)
        self.assertEqual(o.identifier.toPython(), org_url)
        self.assertEqual(o.value(FOAF.name), Literal(org.name))
        self.assertEqual(o.value(RDFS.label), Literal(org.name))
        self.assertEqual(o.value(FOAF.homepage).identifier, URIRef(org.url))

    def test_catalog(self):
        origin_org = OrganizationFactory()
        uri = url_for('organizations.rdf_catalog', org=origin_org.id, _external=True)

        datasets = VisibleDatasetFactory.create_batch(3, organization=origin_org)
        catalog = build_org_catalog(origin_org, datasets)
        
        graph = catalog.graph

        self.assertIsInstance(catalog, RdfResource)
        catalogs = graph.subjects(RDF.type, DCAT.Catalog)
        self.assertEqual(len(list(catalogs)), 1)

        self.assertEqual(catalog.value(RDF.type).identifier, DCAT.Catalog)

        self.assertIsInstance(catalog.identifier, URIRef)
        self.assertEqual(str(catalog.identifier), uri)

        self.assertEqual(len(list(catalog.objects(DCAT.dataset))), len(datasets))

        org = catalog.value(DCT.publisher)
        self.assertEqual(org.value(RDF.type).identifier, FOAF.Organization)
        self.assertEqual(org.value(FOAF.name), Literal(origin_org.name))

        graph = catalog.graph
        graph_datasets = graph.subjects(RDF.type, DCAT.Dataset)
        self.assertEqual(len(list(graph_datasets)), len(datasets))

    def test_catalog_pagination(self):
        origin_org = OrganizationFactory()
        page_size = 3
        total = 4
        uri = url_for('organizations.rdf_catalog', org=origin_org.id, _external=True)
        uri_first = url_for('organizations.rdf_catalog_format', org=origin_org.id, format='json',
                            page=1, page_size=page_size, _external=True)
        uri_last = url_for('organizations.rdf_catalog_format', org=origin_org.id, format='json',
                           page=2, page_size=page_size, _external=True)
        VisibleDatasetFactory.create_batch(total, organization=origin_org)

        # First page
        datasets = Dataset.objects.paginate(1, page_size)
        catalog = build_org_catalog(origin_org, datasets, format='json')
        graph = catalog.graph

        self.assertIsInstance(catalog, RdfResource)
        self.assertEqual(catalog.identifier, URIRef(uri))
        types = [o.identifier for o in catalog.objects(RDF.type)]
        self.assertIn(DCAT.Catalog, types)
        self.assertIn(HYDRA.Collection, types)

        self.assertEqual(catalog.value(HYDRA.totalItems), Literal(total))

        self.assertEqual(len(list(catalog.objects(DCAT.dataset))), page_size)

        paginations = list(graph.subjects(RDF.type,
                                          HYDRA.PartialCollectionView))
        self.assertEqual(len(paginations), 1)
        pagination = graph.resource(paginations[0])
        self.assertEqual(pagination.identifier, URIRef(uri_first))
        self.assertEqual(pagination.value(HYDRA.first).identifier, URIRef(uri_first))
        self.assertEqual(pagination.value(HYDRA.next).identifier, URIRef(uri_last))
        self.assertEqual(pagination.value(HYDRA.last).identifier, URIRef(uri_last))
        self.assertNotIn(HYDRA.previous, pagination)

        # Second page
        datasets = Dataset.objects.paginate(2, page_size)
        catalog = build_org_catalog(origin_org, datasets, format='json')
        graph = catalog.graph

        self.assertIsInstance(catalog, RdfResource)
        self.assertEqual(catalog.identifier, URIRef(uri))
        types = [o.identifier for o in catalog.objects(RDF.type)]
        self.assertIn(DCAT.Catalog, types)
        self.assertIn(HYDRA.Collection, types)

        self.assertEqual(catalog.value(HYDRA.totalItems), Literal(total))

        self.assertEqual(len(list(catalog.objects(DCAT.dataset))), 1)

        paginations = list(graph.subjects(RDF.type,
                                          HYDRA.PartialCollectionView))
        self.assertEqual(len(paginations), 1)
        pagination = graph.resource(paginations[0])
        self.assertEqual(pagination.identifier, URIRef(uri_last))
        self.assertEqual(pagination.value(HYDRA.first).identifier, URIRef(uri_first))
        self.assertEqual(pagination.value(HYDRA.previous).identifier, URIRef(uri_first))
        self.assertEqual(pagination.value(HYDRA.last).identifier, URIRef(uri_last))
        self.assertNotIn(HYDRA.next, pagination)
