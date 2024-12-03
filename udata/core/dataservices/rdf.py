from flask import current_app
from rdflib import RDF, BNode, Graph, Literal, URIRef

from udata.core.dataservices.models import Dataservice
from udata.core.dataservices.models import HarvestMetadata as HarvestDataserviceMetadata
from udata.core.dataset.models import Dataset, License
from udata.core.dataset.rdf import dataset_to_graph_id, sanitize_html
from udata.rdf import (
    DCAT,
    DCATAP,
    DCT,
    HVD_LEGISLATION,
    TAG_TO_EU_HVD_CATEGORIES,
    contact_point_from_rdf,
    contact_point_to_rdf,
    namespace_manager,
    rdf_value,
    remote_url_from_rdf,
    themes_from_rdf,
    url_from_rdf,
)
from udata.uris import endpoint_for


def dataservice_from_rdf(
    graph: Graph,
    dataservice: Dataservice,
    node,
    all_datasets: list[Dataset],
    remote_url_prefix: str | None = None,
) -> Dataservice:
    """
    Create or update a dataset from a RDF/DCAT graph
    """
    if node is None:  # Assume first match is the only match
        node = graph.value(predicate=RDF.type, object=DCAT.DataService)

    d = graph.resource(node)

    dataservice.title = rdf_value(d, DCT.title)
    dataservice.description = sanitize_html(d.value(DCT.description) or d.value(DCT.abstract))

    dataservice.base_api_url = url_from_rdf(d, DCAT.endpointURL)
    dataservice.endpoint_description_url = url_from_rdf(d, DCAT.endpointDescription)

    dataservice.contact_point = contact_point_from_rdf(d, dataservice) or dataservice.contact_point

    datasets = []
    for dataset_node in d.objects(DCAT.servesDataset):
        id = dataset_node.value(DCT.identifier)
        dataset = next(
            (d for d in all_datasets if d is not None and d.harvest.remote_id == id), None
        )

        if dataset is None:
            # We try with `endswith` because Europe XSLT have problems with IDs. Sometimes they are prefixed with the domain of the catalog, sometimes not.
            dataset = next(
                (d for d in all_datasets if d is not None and d.harvest.remote_id.endswith(id)),
                None,
            )

        if dataset is not None:
            datasets.append(dataset.id)

    if datasets:
        dataservice.datasets = datasets

    license = rdf_value(d, DCT.license)
    if license is not None:
        dataservice.license = License.guess(license)

    if not dataservice.harvest:
        dataservice.harvest = HarvestDataserviceMetadata()

    dataservice.harvest.uri = d.identifier.toPython() if isinstance(d.identifier, URIRef) else None
    dataservice.harvest.remote_url = remote_url_from_rdf(
        d, graph, remote_url_prefix=remote_url_prefix
    )
    dataservice.harvest.created_at = rdf_value(d, DCT.issued)
    dataservice.metadata_modified_at = rdf_value(d, DCT.modified)

    dataservice.tags = themes_from_rdf(d)

    return dataservice


def dataservice_to_rdf(dataservice: Dataservice, graph=None):
    """
    Map a dataservice domain model to a DCAT/RDF graph
    """
    # Use the unlocalized permalink to the dataset as URI when available
    # unless there is already an upstream URI
    if dataservice.harvest and dataservice.harvest.uri:
        id = URIRef(dataservice.harvest.uri)
    elif dataservice.id:
        id = URIRef(
            endpoint_for(
                "dataservices.show_redirect",
                "api.dataservice",
                dataservice=dataservice.id,
                _external=True,
            )
        )
    else:
        # Should not happen in production. Some test only
        # `build()` a dataset without saving it to the DB.
        id = BNode()

    # Expose upstream identifier if present
    if dataservice.harvest:
        identifier = dataservice.harvest.remote_id
    else:
        identifier = dataservice.id
    graph = graph or Graph(namespace_manager=namespace_manager)

    d = graph.resource(id)
    d.set(RDF.type, DCAT.DataService)
    d.set(DCT.identifier, Literal(identifier))
    d.set(DCT.title, Literal(dataservice.title))
    d.set(DCT.description, Literal(dataservice.description))
    d.set(DCT.issued, Literal(dataservice.created_at))

    if dataservice.base_api_url:
        d.set(DCAT.endpointURL, URIRef(dataservice.base_api_url))

    if dataservice.harvest and dataservice.harvest.remote_url:
        d.set(DCAT.landingPage, URIRef(dataservice.harvest.remote_url))
    elif dataservice.id:
        d.set(
            DCAT.landingPage,
            URIRef(
                endpoint_for(
                    "dataservices.show_redirect",
                    "api.dataservice",
                    dataservice=dataservice.id,
                    _external=True,
                )
            ),
        )

    if dataservice.endpoint_description_url:
        d.set(DCAT.endpointDescription, URIRef(dataservice.endpoint_description_url))

    # Add DCAT-AP HVD properties if the dataservice is tagged hvd.
    # See https://semiceu.github.io/DCAT-AP/releases/2.2.0-hvd/
    is_hvd = current_app.config["HVD_SUPPORT"] and "hvd" in dataservice.tags
    if is_hvd:
        d.add(DCATAP.applicableLegislation, URIRef(HVD_LEGISLATION))

    hvd_category_tags = set()
    for tag in dataservice.tags:
        d.add(DCAT.keyword, Literal(tag))
        # Add HVD category if this dataservice is tagged HVD
        if is_hvd and tag in TAG_TO_EU_HVD_CATEGORIES:
            hvd_category_tags.add(tag)

    if is_hvd:
        # We also want to automatically add any HVD category tags of the dataservice's datasets.
        for dataset in dataservice.datasets:
            if "hvd" not in dataset.tags:  # Only check HVD datasets for their categories.
                continue
            for tag in dataset.tags:
                if tag in TAG_TO_EU_HVD_CATEGORIES:
                    hvd_category_tags.add(tag)
    for tag in hvd_category_tags:
        d.add(DCATAP.hvdCategory, URIRef(TAG_TO_EU_HVD_CATEGORIES[tag]))

    # `dataset_to_graph_id(dataset)` URIRef may not exist in the current page
    # but should exists in the catalog somewhere. Maybe we should create a Node
    # with some basic information about this dataset (but this will return a page
    # with more datasets than the page size… and could be problematic when processing the
    # correct Node with all the information in a future page)
    if str(dataservice.id) == current_app.config["TABULAR_API_DATASERVICE_ID"]:
        # TODO: remove this condition on TABULAR_API_DATASERVICE_ID.
        # It is made to prevent having the graph explode due to too many datasets being served.
        pass
    else:
        for dataset in dataservice.datasets:
            d.add(DCAT.servesDataset, dataset_to_graph_id(dataset))

    contact_point = contact_point_to_rdf(dataservice.contact_point, graph)
    if contact_point:
        d.set(DCAT.contactPoint, contact_point)

    return d
