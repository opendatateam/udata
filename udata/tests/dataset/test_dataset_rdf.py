# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from datetime import datetime
from uuid import uuid4

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import Namespace, RDF, SKOS, FOAF

from udata.models import Dataset, License
from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.dataset.rdf import dataset_to_rdf, dataset_from_rdf
from udata.core.dataset.views import blueprint as dataset_blueprint
from udata.tests import TestCase, DBTestMixin
from udata.core.organization.factories import OrganizationFactory
from udata.utils import faker
from udata.rdf import DCAT, DCT


class DatasetToRdf(DBTestMixin, TestCase):
    def create_app(self):
        app = super(DatasetToRdf, self).create_app()
        app.register_blueprint(dataset_blueprint)
        return app

    def test_minimal(self):
        dataset = DatasetFactory.build()  # Does not have an URL
        g = dataset_to_rdf(dataset)

        self.assertIsInstance(g, Graph)
        self.assertEqual(len(list(g.subjects(RDF.type, DCAT.Dataset))), 1)

        node = g.value(predicate=RDF.type, object=DCAT.Dataset)

        self.assertIsInstance(node, BNode)
        self.assertEqual(g.value(node, DCT.identifier), Literal(dataset.id))
        self.assertEqual(g.value(node, DCT.title), Literal(dataset.title))

    def test_all_dataset_fields(self):
        dataset = DatasetFactory()
        g = dataset_to_rdf(dataset)

        self.assertIsInstance(g, Graph)
        self.assertEqual(len(list(g.subjects(RDF.type, DCAT.Dataset))), 1)

        node = g.value(predicate=RDF.type, object=DCAT.Dataset)

        self.assertIsInstance(node, URIRef)
        uri = url_for('datasets.show_redirect', dataset=dataset.id, _external=True)
        self.assertEqual(str(node), uri)
        self.assertEqual(g.value(node, DCT.identifier), Literal(dataset.id))
        self.assertEqual(g.value(node, DCT.title), Literal(dataset.title))

    def test_minimal_resource_fields(self):
        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])

        g = dataset_to_rdf(dataset)
        node = g.value(predicate=RDF.type, object=DCAT.Dataset)

    def test_all_resource_fields(self):
        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])

        g = dataset_to_rdf(dataset)
        node = g.value(predicate=RDF.type, object=DCAT.Dataset)

    def test_spatial_coverage(self):
        dataset = DatasetFactory()

        g = dataset_to_rdf(dataset)
        node = g.value(predicate=RDF.type, object=DCAT.Dataset)

    def test_time_coverage(self):
        dataset = DatasetFactory()

        g = dataset_to_rdf(dataset)
        node = g.value(predicate=RDF.type, object=DCAT.Dataset)

    def test_from_external_repository(self):
        dataset = DatasetFactory(extras={
            'dct:identifier': 'an-identifier',
            'uri': 'https://somewhere.org/dataset',
        })

        g = dataset_to_rdf(dataset)
        node = g.value(predicate=RDF.type, object=DCAT.Dataset)

        self.assertIsInstance(node, URIRef)
        self.assertEqual(str(node), 'https://somewhere.org/dataset')
        self.assertEqual(g.value(node, DCT.identifier), Literal('an-identifier'))


class RdfToDatasetTest(DBTestMixin, TestCase):
    def test_minimal(self):
        node = BNode()
        g = Graph()

        title = faker.sentence()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(title)))

        dataset = dataset_from_rdf(g)

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(dataset.title, title)

    def test_update(self):
        original = DatasetFactory()

        node = URIRef('https://test.org/dataset')
        g = Graph()

        new_title = faker.sentence()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(new_title)))

        dataset = dataset_from_rdf(g, dataset=original)

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(dataset.id, original.id)
        self.assertEqual(dataset.title, new_title)

    def test_all_fields(self):
        uri = 'https://test.org/dataset'
        node = URIRef(uri)
        g = Graph()

        title = faker.sentence()
        id = faker.uuid4()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.identifier, Literal(id)))
        g.add((node, DCT.title, Literal(title)))

        dataset = dataset_from_rdf(g)

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(dataset.title, title)

        extras = dataset.extras
        self.assertIn('dct:identifier', extras)
        self.assertEqual(extras['dct:identifier'], id)
        self.assertIn('uri', extras)
        self.assertEqual(extras['uri'], uri)
