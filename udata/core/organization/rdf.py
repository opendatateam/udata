'''
This module centralize organization helpers
for RDF/DCAT serialization and parsing
'''

from flask import url_for
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, FOAF

from udata.rdf import DCAT, DCT, HYDRA, namespace_manager

from udata.core.dataset.rdf import dataset_to_rdf
from udata.utils import Paginable


def organization_to_rdf(org, graph=None):
    '''
    Map a Resource domain model to a DCAT/RDF graph
    '''
    graph = graph or Graph(namespace_manager=namespace_manager)
    if org.id:
        org_url = url_for('organizations.show_redirect',
                          org=org.id,
                          _external=True)
        id = URIRef(org_url)
    else:
        id = BNode()
    o = graph.resource(id)
    o.set(RDF.type, FOAF.Organization)
    o.set(FOAF.name, Literal(org.name))
    o.set(RDFS.label, Literal(org.name))
    if org.url:
        o.set(FOAF.homepage, URIRef(org.url))

    return o


def build_org_catalog(org, datasets, format=None):
    graph = Graph(namespace_manager=namespace_manager)
    org_catalog_url = url_for('organizations.rdf_catalog', org=org.id, _external=True)

    catalog = graph.resource(URIRef(org_catalog_url))
    catalog.set(RDF.type, DCAT.Catalog)
    catalog.set(DCT.publisher, organization_to_rdf(org, graph))

    for dataset in datasets:
        catalog.add(DCAT.dataset, dataset_to_rdf(dataset, graph))
    
    if isinstance(datasets, Paginable):
        if not format:
            raise ValueError('Pagination requires format')
        catalog.add(RDF.type, HYDRA.Collection)
        catalog.set(HYDRA.totalItems, Literal(datasets.total))
        kwargs = {
            'format': format,
            'page_size': datasets.page_size,
            '_external': True,
        }

        first_url = url_for('organizations.rdf_catalog_format',
                            org=org.id, page=1, **kwargs)
        page_url = url_for('organizations.rdf_catalog_format',
                            org=org.id, page=datasets.page, **kwargs)
        last_url = url_for('organizations.rdf_catalog_format',
                           org=org.id, page=datasets.pages, **kwargs)
        pagination = graph.resource(URIRef(page_url))
        pagination.set(RDF.type, HYDRA.PartialCollectionView)

        pagination.set(HYDRA.first, URIRef(first_url))
        pagination.set(HYDRA.last, URIRef(last_url))
        if datasets.has_next:
            next_url = url_for('organizations.rdf_catalog_format',
                               org=org.id, page=datasets.page + 1, **kwargs)
            pagination.set(HYDRA.next, URIRef(next_url))
        if datasets.has_prev:
            prev_url = url_for('organizations.rdf_catalog_format',
                               org=org.id, page=datasets.page - 1, **kwargs)
            pagination.set(HYDRA.previous, URIRef(prev_url))

        catalog.set(HYDRA.view, pagination)
    
    return catalog
