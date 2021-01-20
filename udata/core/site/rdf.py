'''
This module centralize site helpers for RDF/DCAT serialization and parsing
'''
from flask import url_for, current_app
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, FOAF

from udata.core.dataset.rdf import dataset_to_rdf
from udata.core.organization.rdf import organization_to_rdf
from udata.core.user.rdf import user_to_rdf
from udata.rdf import DCAT, DCT, HYDRA, namespace_manager, paginate_catalog
from udata.utils import Paginable


def build_catalog(site, datasets, format=None):
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
        rdf_dataset = dataset_to_rdf(dataset, graph)
        if dataset.owner:
            rdf_dataset.add(DCT.publisher, user_to_rdf(dataset.owner, graph))
        elif dataset.organization:
            rdf_dataset.add(DCT.publisher, organization_to_rdf(dataset.organization, graph))
        catalog.add(DCAT.dataset, rdf_dataset)

    if isinstance(datasets, Paginable):
        paginate_catalog(catalog, graph, datasets, format, 'site.rdf_catalog_format')

    return catalog
