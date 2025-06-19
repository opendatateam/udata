"""
This module centralize site helpers for RDF/DCAT serialization and parsing
"""

from flask import current_app, url_for
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import FOAF, RDF

from udata.core.dataservices.rdf import dataservice_to_rdf
from udata.core.dataset.rdf import dataset_to_rdf
from udata.core.organization.rdf import organization_to_rdf
from udata.core.user.rdf import user_to_rdf
from udata.rdf import DCAT, DCT, namespace_manager, paginate_catalog
from udata.uris import homepage_url
from udata.utils import Paginable


def build_catalog(site, datasets, dataservices=[], format=None):
    """Build the DCAT catalog for this site"""
    catalog_url = url_for("api.site_rdf_catalog", _external=True)
    graph = Graph(namespace_manager=namespace_manager)
    catalog = graph.resource(URIRef(catalog_url))

    catalog.set(RDF.type, DCAT.Catalog)
    catalog.set(DCT.title, Literal(site.title))
    catalog.set(DCT.description, Literal(f"{site.title}"))
    catalog.set(DCT.language, Literal(current_app.config["DEFAULT_LANGUAGE"]))
    catalog.set(FOAF.homepage, URIRef(homepage_url(_external=True)))

    publisher = graph.resource(BNode())
    publisher.set(RDF.type, FOAF.Organization)
    publisher.set(FOAF.name, Literal(current_app.config["SITE_AUTHOR"]))
    catalog.set(DCT.publisher, publisher)

    for dataset in datasets:
        rdf_dataset = dataset_to_rdf(dataset, graph)
        if dataset.owner:
            rdf_dataset.add(DCT.publisher, user_to_rdf(dataset.owner, graph))
        elif dataset.organization:
            rdf_dataset.add(DCT.publisher, organization_to_rdf(dataset.organization, graph))
        catalog.add(DCAT.dataset, rdf_dataset)

    for dataservice in dataservices:
        rdf_dataservice = dataservice_to_rdf(dataservice, graph)
        catalog.add(DCAT.service, rdf_dataservice)

    if isinstance(datasets, Paginable):
        paginate_catalog(catalog, graph, datasets, format, "api.site_rdf_catalog_format")

    return catalog
