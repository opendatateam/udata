from rdflib import RDF, BNode, Graph, Literal, URIRef

from udata.core.dataservices.models import Dataservice
from udata.core.dataservices.models import HarvestMetadata as HarvestDataserviceMetadata
from udata.core.dataset.models import Dataset, License
from udata.core.dataset.rdf import dataset_to_graph_id, sanitize_html
from udata.rdf import (
    DCAT,
    DCT,
    contact_point_from_rdf,
    namespace_manager,
    rdf_value,
    remote_url_from_rdf,
    themes_from_rdf,
    url_from_rdf,
)
from udata.uris import endpoint_for


def dataservice_from_rdf(
    graph: Graph, dataservice: Dataservice, node, all_datasets: list[Dataset]
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
    dataservice.harvest.remote_url = remote_url_from_rdf(d)
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
        d.set(DCAT.endpointURL, Literal(dataservice.base_api_url))

    if dataservice.endpoint_description_url:
        d.set(DCAT.endpointDescription, Literal(dataservice.endpoint_description_url))

    for tag in dataservice.tags:
        d.add(DCAT.keyword, Literal(tag))

    # `dataset_to_graph_id(dataset)` URIRef may not exist in the current page
    # but should exists in the catalog somewhere. Maybe we should create a Node
    # with some basic information about this dataset (but this will return a page
    # with more datasets than the page size… and could be problematic when processing the
    # correct Node with all the information in a future page)
    for dataset in dataservice.datasets:
        d.add(DCAT.servesDataset, dataset_to_graph_id(dataset))

    return d
