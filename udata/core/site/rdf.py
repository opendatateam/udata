# -*- coding: utf-8 -*-
from __future__ import unicode_literals
'''
This module centralize site helpers for RDF/DCAT serialization and parsing
'''
from flask import url_for, current_app
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, FOAF

from udata.core.dataset.models import Dataset
from udata.core.dataset.rdf import dataset_to_rdf
from udata.rdf import DCAT, DCT, HYDRA, namespace_manager
from udata.utils import Paginable


def build_catalog(site, datasets):
    '''Build the DCAT catalog for this site'''
    site_url = url_for('site.home_redirect', _external=True)
    catalog_url = url_for('site.rdf_catalog', _external=True)
    graph = Graph(namespace_manager=namespace_manager)
    catalog = graph.resource(URIRef(catalog_url))

    catalog.set(RDF.type, DCAT.Catalog)
    catalog.set(DCT.title, Literal(site.title))
    catalog.set(DCT.language,
                Literal(current_app.config['DEFAULT_LANGUAGE']))
    catalog.set(FOAF.homepage, URIRef(site_url))

    publisher = graph.resource(BNode())
    publisher.set(RDF.type, FOAF.Organization)
    publisher.set(FOAF.name, Literal(current_app.config['SITE_AUTHOR']))
    catalog.set(DCT.publisher, publisher)

    for dataset in datasets:
        catalog.add(DCAT.dataset, dataset_to_rdf(dataset, graph))

    if isinstance(datasets, Paginable):
        catalog.add(RDF.type, HYDRA.Collection)
        catalog.set(HYDRA.totalItems, Literal(datasets.total))

        first_url = url_for('site.rdf_catalog', page=1, _external=True)
        page_url = url_for('site.rdf_catalog', page=datasets.page,
                           _external=True)
        last_url = url_for('site.rdf_catalog', page=datasets.pages,
                           _external=True)
        pagination = graph.resource(URIRef(page_url))
        pagination.set(RDF.type, HYDRA.PartialCollectionView)

        pagination.set(HYDRA.first, URIRef(first_url))
        pagination.set(HYDRA.last, URIRef(last_url))
        if datasets.has_next:
            next_url = url_for('site.rdf_catalog', page=datasets.page + 1,
                               _external=True)
            pagination.set(HYDRA.next, URIRef(next_url))
        if datasets.has_prev:
            prev_url = url_for('site.rdf_catalog', page=datasets.page - 1,
                               _external=True)
            pagination.set(HYDRA.previous, URIRef(prev_url))

        catalog.set(HYDRA.view, pagination)

    return catalog
