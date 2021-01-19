'''
This module centralize organization helpers
for RDF/DCAT serialization and parsing
'''

from flask import url_for
from rdflib import Graph, URIRef, Literal, BNode
from udata.rdf import DCAT
from rdflib.namespace import RDF, RDFS, FOAF

from udata.core.dataset.rdf import dataset_to_rdf
from udata.rdf import namespace_manager


def organization_to_rdf(org, datasets, graph=None):
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

    for dataset in datasets:
        o.add(DCAT.dataset, dataset_to_rdf(dataset, graph))

    return o
