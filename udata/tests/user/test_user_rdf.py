from flask import url_for
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import FOAF, RDF, RDFS
from rdflib.resource import Resource as RdfResource

from udata import api
from udata.core.user.factories import UserFactory
from udata.core.user.rdf import user_to_rdf
from udata.tests import DBTestMixin, TestCase
from udata.utils import faker


class UserToRdfTest(DBTestMixin, TestCase):
    def create_app(self):
        app = super(UserToRdfTest, self).create_app()
        api.init_app(app)
        return app

    def test_minimal(self):
        user = UserFactory.build()  # Does not have an URL
        u = user_to_rdf(user)
        g = u.graph

        self.assertIsInstance(u, RdfResource)
        self.assertEqual(len(list(g.subjects(RDF.type, FOAF.Person))), 1)

        self.assertEqual(u.value(RDF.type).identifier, FOAF.Person)

        self.assertIsInstance(u.identifier, BNode)
        self.assertEqual(u.value(FOAF.name), Literal(user.fullname))
        self.assertEqual(u.value(RDFS.label), Literal(user.fullname))

    def test_all_fields(self):
        user = UserFactory(website=faker.uri())
        user_url = url_for("api.user", user=user.id, _external=True)
        u = user_to_rdf(user)
        g = u.graph

        self.assertIsInstance(u, RdfResource)
        self.assertEqual(len(list(g.subjects(RDF.type, FOAF.Person))), 1)

        self.assertEqual(u.value(RDF.type).identifier, FOAF.Person)

        self.assertIsInstance(u.identifier, URIRef)
        self.assertEqual(u.identifier.toPython(), user_url)
        self.assertEqual(u.value(FOAF.name), Literal(user.fullname))
        self.assertEqual(u.value(RDFS.label), Literal(user.fullname))
        self.assertEqual(u.value(FOAF.homepage).identifier, URIRef(user.website))
