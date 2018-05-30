from flask import url_for

from rdflib import URIRef, Literal, BNode
from rdflib.namespace import RDF, FOAF, RDFS
from rdflib.resource import Resource as RdfResource

from udata.tests import TestCase, DBTestMixin
from udata.core.organization.views import blueprint as org_blueprint
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.rdf import organization_to_rdf
from udata.utils import faker


class OrganizationToRdfTest(DBTestMixin, TestCase):
    def create_app(self):
        app = super(OrganizationToRdfTest, self).create_app()
        app.register_blueprint(org_blueprint)
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
