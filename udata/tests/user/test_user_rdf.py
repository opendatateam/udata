# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from rdflib import URIRef, Literal, BNode
from rdflib.namespace import RDF, FOAF, RDFS
from rdflib.resource import Resource as RdfResource

from udata.tests import TestCase, DBTestMixin
from udata.core.user.views import blueprint as user_blueprint
from udata.core.user.factories import UserFactory
from udata.core.user.rdf import user_to_rdf
from udata.utils import faker


class UserToRdfTest(DBTestMixin, TestCase):
    def create_app(self):
        app = super(UserToRdfTest, self).create_app()
        app.register_blueprint(user_blueprint)
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
        user_url = url_for('users.show_redirect',
                           user=user.id,
                           _external=True)
        u = user_to_rdf(user)
        g = u.graph

        self.assertIsInstance(u, RdfResource)
        self.assertEqual(len(list(g.subjects(RDF.type, FOAF.Person))), 1)

        self.assertEqual(u.value(RDF.type).identifier, FOAF.Person)

        self.assertIsInstance(u.identifier, URIRef)
        self.assertEqual(u.identifier.toPython(), user_url)
        self.assertEqual(u.value(FOAF.name), Literal(user.fullname))
        self.assertEqual(u.value(RDFS.label), Literal(user.fullname))
        self.assertEqual(u.value(FOAF.homepage).identifier,
                         URIRef(user.website))
