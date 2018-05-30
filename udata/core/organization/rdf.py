'''
This module centralize organization helpers
for RDF/DCAT serialization and parsing
'''

from flask import url_for
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, FOAF

from udata.rdf import namespace_manager


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
