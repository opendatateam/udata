'''
This module centralize site helpers for RDF/DCAT serialization and parsing
'''
from flask import url_for, current_app
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, FOAF

from udata.core.dataset.rdf import dataset_to_rdf
from udata.core.organization.rdf import organization_to_rdf
from udata.core.user.rdf import user_to_rdf
from udata.rdf import DCAT, DCT, namespace_manager, paginate_catalog
from udata.utils import Paginable
from udata.uris import endpoint_for


def build_catalog(site, datasets, dataservices = [], format=None):
    '''Build the DCAT catalog for this site'''
    site_url = endpoint_for('site.home_redirect', 'api.site', _external=True)
    catalog_url = url_for('api.site_rdf_catalog', _external=True)
    graph = Graph(namespace_manager=namespace_manager)
    catalog = graph.resource(URIRef(catalog_url))

    catalog.set(RDF.type, DCAT.Catalog)
    catalog.set(DCT.title, Literal(site.title))
    catalog.set(DCT.description, Literal(f"{site.title}"))
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

    for dataservice in dataservices:
        if dataservice.harvest and dataservice.harvest.uri:
            id = URIRef(dataservice.harvest.uri)
        elif dataservice.id:
            id = URIRef(endpoint_for('dataservices.show_redirect', 'api.dataservice',
                        dataservice=dataservice.id, _external=True))

        if dataservice.harvest and dataservice.harvest.dct_identifier:
            identifier = dataservice.harvest.dct_identifier
        else:
            identifier = dataservice.id

        d = graph.resource(id)
        d.set(RDF.type, DCAT.DataService)
        d.set(DCT.identifier, Literal(identifier))
        d.set(DCT.title, Literal(dataservice.title))
        d.set(DCT.description, Literal(dataservice.description))
        for serve in dataset.dataservices:
            d.add(DCAT.Serves, URIRef('http://example.org'))


    if isinstance(datasets, Paginable):
        paginate_catalog(catalog, graph, datasets, format, 'api.site_rdf_catalog_format')

    return catalog
