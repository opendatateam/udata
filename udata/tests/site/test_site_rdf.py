# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import current_app, url_for

from rdflib import URIRef, Literal, Graph
from rdflib.namespace import RDF, FOAF
from rdflib.resource import Resource

from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.site.factories import SiteFactory
from udata.core.site.rdf import build_catalog
from udata.core.user.factories import UserFactory
from udata.rdf import CONTEXT, DCAT, DCT, HYDRA
from udata.tests.frontend import FrontTestCase


class CatalogTest(FrontTestCase):
    modules = ['core.dataset', 'core.organization', 'core.user', 'core.site']

    def test_minimal(self):
        site = SiteFactory()
        home_url = url_for('site.home_redirect', _external=True)
        uri = url_for('site.rdf_catalog', _external=True)
        datasets = VisibleDatasetFactory.create_batch(3)
        catalog = build_catalog(site, datasets)
        graph = catalog.graph

        self.assertIsInstance(catalog, Resource)
        catalogs = graph.subjects(RDF.type, DCAT.Catalog)
        self.assertEqual(len(list(catalogs)), 1)

        self.assertEqual(catalog.value(RDF.type).identifier, DCAT.Catalog)

        self.assertIsInstance(catalog.identifier, URIRef)
        self.assertEqual(str(catalog.identifier), uri)
        self.assertEqual(catalog.value(DCT.title), Literal(site.title))
        self.assertEqual(catalog.value(DCT.language),
                         Literal(self.app.config['DEFAULT_LANGUAGE']))

        self.assertEqual(len(list(catalog.objects(DCAT.dataset))),
                         len(datasets))

        self.assertEqual(catalog.value(FOAF.homepage).identifier,
                         URIRef(home_url))

        org = catalog.value(DCT.publisher)
        self.assertEqual(org.value(RDF.type).identifier, FOAF.Organization)
        self.assertEqual(org.value(FOAF.name),
                         Literal(current_app.config['SITE_AUTHOR']))

        graph = catalog.graph
        self.assertEqual(len(list(graph.subjects(RDF.type, DCAT.Dataset))),
                         len(datasets))

    def test_no_duplicate(self):
        site = SiteFactory()
        org = OrganizationFactory()
        user = UserFactory()
        datasets = VisibleDatasetFactory.create_batch(2, owner=user)
        datasets += VisibleDatasetFactory.create_batch(2, organization=org)
        catalog = build_catalog(site, datasets)
        graph = catalog.graph

        orgs = list(graph.subjects(RDF.type, FOAF.Organization))
        self.assertEqual(len(orgs), 1 + 1)  # There is the site publisher
        users = list(graph.subjects(RDF.type, FOAF.Person))
        self.assertEqual(len(users), 1)
        org_names = list(graph.objects(orgs[0], FOAF.name))
        self.assertEqual(len(org_names), 1)
        user_names = list(graph.objects(users[0], FOAF.name))
        self.assertEqual(len(user_names), 1)

    def test_pagination(self):
        site = SiteFactory()
        page_size = 3
        total = 4
        uri = url_for('site.rdf_catalog', _external=True)
        uri_first = url_for('site.rdf_catalog_format', format='json',
                            page=1, page_size=page_size, _external=True)
        uri_last = url_for('site.rdf_catalog_format', format='json',
                           page=2, page_size=page_size, _external=True)
        VisibleDatasetFactory.create_batch(total)

        # First page
        datasets = Dataset.objects.paginate(1, page_size)
        catalog = build_catalog(site, datasets, format='json')
        graph = catalog.graph

        self.assertIsInstance(catalog, Resource)
        self.assertEqual(catalog.identifier, URIRef(uri))
        types = [o.identifier for o in catalog.objects(RDF.type)]
        self.assertIn(DCAT.Catalog, types)
        self.assertIn(HYDRA.Collection, types)

        self.assertEqual(catalog.value(HYDRA.totalItems), Literal(total))

        self.assertEqual(len(list(catalog.objects(DCAT.dataset))),
                         page_size)

        paginations = list(graph.subjects(RDF.type, HYDRA.PartialCollectionView))
        self.assertEqual(len(paginations), 1)
        pagination = graph.resource(paginations[0])
        self.assertEqual(pagination.identifier, URIRef(uri_first))
        self.assertEqual(pagination.value(HYDRA.first).identifier,
                         URIRef(uri_first))
        self.assertEqual(pagination.value(HYDRA.next).identifier,
                         URIRef(uri_last))
        self.assertEqual(pagination.value(HYDRA.last).identifier,
                         URIRef(uri_last))
        self.assertNotIn(HYDRA.previous, pagination)

        # Second page
        datasets = Dataset.objects.paginate(2, page_size)
        catalog = build_catalog(site, datasets, format='json')
        graph = catalog.graph

        self.assertIsInstance(catalog, Resource)
        self.assertEqual(catalog.identifier, URIRef(uri))
        types = [o.identifier for o in catalog.objects(RDF.type)]
        self.assertIn(DCAT.Catalog, types)
        self.assertIn(HYDRA.Collection, types)

        self.assertEqual(catalog.value(HYDRA.totalItems), Literal(total))

        self.assertEqual(len(list(catalog.objects(DCAT.dataset))),
                         1)

        paginations = list(graph.subjects(RDF.type, HYDRA.PartialCollectionView))
        self.assertEqual(len(paginations), 1)
        pagination = graph.resource(paginations[0])
        self.assertEqual(pagination.identifier, URIRef(uri_last))
        self.assertEqual(pagination.value(HYDRA.first).identifier,
                         URIRef(uri_first))
        self.assertEqual(pagination.value(HYDRA.previous).identifier,
                         URIRef(uri_first))
        self.assertEqual(pagination.value(HYDRA.last).identifier,
                         URIRef(uri_last))
        self.assertNotIn(HYDRA.next, pagination)


class SiteRdfViewsTest(FrontTestCase):
    modules = ['core.site', 'core.dataset']

    def test_expose_jsonld_context(self):
        url = url_for('site.jsonld_context')
        self.assertEqual(url, '/context.jsonld')

        response = self.get(url)
        self.assert200(response)
        self.assertEqual(response.content_type, 'application/ld+json')
        self.assertEqual(response.json, CONTEXT)

    def test_catalog_default_to_jsonld(self):
        expected = url_for('site.rdf_catalog_format', format='json')
        response = self.get(url_for('site.rdf_catalog'))
        self.assertRedirects(response, expected)

    def test_rdf_perform_content_negociation(self):
        expected = url_for('site.rdf_catalog_format', format='xml')
        url = url_for('site.rdf_catalog')
        headers = {'accept': 'application/xml'}
        response = self.get(url, headers=headers)
        self.assertRedirects(response, expected)

    def test_catalog_rdf_json_ld(self):
        for fmt in 'json', 'jsonld':
            url = url_for('site.rdf_catalog_format', format=fmt)
            response = self.get(url)
            self.assert200(response)
            self.assertEqual(response.content_type, 'application/ld+json')
            context_url = url_for('site.jsonld_context', _external=True)
            self.assertEqual(response.json['@context'], context_url)

    def test_catalog_rdf_n3(self):
        url = url_for('site.rdf_catalog_format', format='n3')
        response = self.get(url)
        self.assert200(response)
        self.assertEqual(response.content_type, 'text/n3')

    def test_catalog_rdf_turtle(self):
        url = url_for('site.rdf_catalog_format', format='ttl')
        response = self.get(url)
        self.assert200(response)
        self.assertEqual(response.content_type, 'application/x-turtle')

    def test_catalog_rdf_rdfxml(self):
        for fmt in 'xml', 'rdf', 'rdfs', 'owl':
            url = url_for('site.rdf_catalog_format', format=fmt)
            response = self.get(url)
            self.assert200(response)
            self.assertEqual(response.content_type, 'application/rdf+xml')

    def test_catalog_rdf_n_triples(self):
        url = url_for('site.rdf_catalog_format', format='nt')
        response = self.get(url)
        self.assert200(response)
        self.assertEqual(response.content_type, 'application/n-triples')

    def test_catalog_rdf_trig(self):
        url = url_for('site.rdf_catalog_format', format='trig')
        response = self.get(url)
        self.assert200(response)
        self.assertEqual(response.content_type, 'application/trig')

    def test_dataportal_compliance(self):
        for fmt in 'json', 'xml', 'ttl':
            url = url_for('site.dataportal', format=fmt)
            self.assertEqual(url, '/data.{0}'.format(fmt))
            expected_url = url_for('site.rdf_catalog_format', format=fmt)

            response = self.get(url)
            self.assertRedirects(response, expected_url)

    def test_catalog_rdf_paginate(self):
        VisibleDatasetFactory.create_batch(4)
        url = url_for('site.rdf_catalog_format', format='n3', page_size=3)
        next_url = url_for('site.rdf_catalog_format', format='n3',
                           page=2, page_size=3, _external=True)

        response = self.get(url)
        self.assert200(response)

        graph = Graph().parse(data=response.data, format='n3')
        pagination = graph.value(predicate=RDF.type,
                                 object=HYDRA.PartialCollectionView)
        self.assertIsNotNone(pagination)
        pagination = graph.resource(pagination)
        self.assertFalse(pagination.value(HYDRA.previous))
        self.assertEqual(pagination.value(HYDRA.next).identifier,
                         URIRef(next_url))
