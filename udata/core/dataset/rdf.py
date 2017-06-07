# -*- coding: utf-8 -*-
from __future__ import unicode_literals
'''
This module centralize dataset helpers for RDF/DCAT serialization and parsing
'''

from flask import url_for
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, SKOS, FOAF

from udata.rdf import DCAT, DCT

from .models import Dataset


def resource_to_rdf(resource):
    '''
    Map a Resource domain model to a DCAT/RDF graph
    '''
    pass


def dataset_to_rdf(dataset):
    '''
    Map a dataset domain model to a DCAT/RDF graph
    '''
    # Use the unlocalized permalink to the dataset as URI when available
    # unless there is already an upstream URI
    if 'uri' in dataset.extras:
        node = URIRef(dataset.extras['uri'])
    elif dataset.id:
        node = URIRef(url_for('datasets.show_redirect',
                              dataset=dataset.id,
                              _external=True))
    else:
        node = BNode()
    # Expose upstream identifier if present
    if 'dct:identifier' in dataset.extras:
        identifier = dataset.extras['dct:identifier']
    else:
        identifier = dataset.id
    g = Graph()
    g.add((node, RDF.type, DCAT.Dataset))
    g.add((node, DCT.identifier, Literal(identifier)))
    g.add((node, DCT.title, Literal(dataset.title)))
    return g


def resource_from_rdf(graph):
    '''
    Map a Resource domain model to a DCAT/RDF graph
    '''
    pass


def dataset_from_rdf(graph, dataset=None):
    '''
    Create or update a dataset from a RDF/DCAT graph
    '''
    dataset = dataset or Dataset()

    node = graph.value(predicate=RDF.type, object=DCAT.Dataset)

    dataset.title = str(graph.value(node, DCT.title))

    dataset.extras['dct:identifier'] = str(graph.value(node, DCT.identifier))

    if isinstance(node, URIRef):
        dataset.extras['uri'] = str(node)

    return dataset
