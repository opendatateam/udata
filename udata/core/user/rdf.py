# -*- coding: utf-8 -*-
from __future__ import unicode_literals
'''
This module centralize user helpers for RDF/DCAT serialization and parsing
'''

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, FOAF

from udata.rdf import namespace_manager


def user_to_rdf(user, graph=None):
    '''
    Map a Resource domain model to a DCAT/RDF graph
    '''
    graph = graph or Graph(namespace_manager=namespace_manager)
    id = Literal(user.id) if user.id else BNode()
    o = graph.resource(id)
    o.set(RDF.type, FOAF.Person)
    o.set(FOAF.name, Literal(user.fullname))
    o.set(RDFS.label, Literal(user.fullname))
    if user.website:
        o.set(FOAF.homepage, URIRef(user.website))
    return o
