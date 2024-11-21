"""
This module centralize organization helpers
for RDF/DCAT serialization and parsing
"""

from flask import url_for
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import FOAF, RDF, RDFS

from udata.core.dataservices.rdf import dataservice_to_rdf
from udata.core.dataset.rdf import dataset_to_rdf
from udata.rdf import DCAT, DCT, namespace_manager, paginate_catalog
from udata.uris import endpoint_for
from udata.utils import Paginable


def organization_to_rdf(org, graph=None):
    """
    Map a Resource domain model to a DCAT/RDF graph
    """
    graph = graph or Graph(namespace_manager=namespace_manager)
    if org.id:
        org_url = endpoint_for(
            "organizations.show_redirect", "api.organization", org=org.id, _external=True
        )
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


def build_org_catalog(org, datasets, dataservices, format=None):
    graph = Graph(namespace_manager=namespace_manager)
    org_catalog_url = url_for("api.organization_rdf", org=org.id, _external=True)

    catalog = graph.resource(URIRef(org_catalog_url))
    catalog.set(RDF.type, DCAT.Catalog)
    catalog.set(DCT.publisher, organization_to_rdf(org, graph))
    catalog.set(DCT.title, Literal(f"{org.name}"))
    catalog.set(DCT.description, Literal(f"{org.name}"))

    for dataset in datasets:
        catalog.add(DCAT.dataset, dataset_to_rdf(dataset, graph))
    for dataservice in dataservices:
        catalog.add(DCAT.service, dataservice_to_rdf(dataservice, graph))

    values = {"org": org.id}

    if isinstance(datasets, Paginable):
        paginate_catalog(catalog, graph, datasets, format, "api.organization_rdf_format", **values)

    return catalog
