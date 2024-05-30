
from datetime import datetime
from typing import List, Optional
from rdflib import RDF, Graph

from udata.core.dataservices.models import Dataservice, HarvestMetadata
from udata.core.dataset.models import Dataset, License
from udata.core.dataset.rdf import sanitize_html
from udata.harvest.models import HarvestSource
from udata.rdf import DCAT, DCT, contact_point_from_rdf, rdf_value, theme_labels_from_rdf, themes_from_rdf, url_from_rdf


def dataservice_from_rdf(graph: Graph, dataservice: Dataservice, node, datasets: List[Dataset]) -> Dataservice :
    '''
    Create or update a dataset from a RDF/DCAT graph
    '''
    if node is None:  # Assume first match is the only match
        node = graph.value(predicate=RDF.type, object=DCAT.DataService)

    d = graph.resource(node)

    dataservice.title = rdf_value(d, DCT.title)
    dataservice.description = sanitize_html(d.value(DCT.description) or d.value(DCT.abstract))

    dataservice.base_api_url = url_from_rdf(d, DCAT.endpointURL)
    dataservice.endpoint_description_url = url_from_rdf(d, DCAT.endpointDescription)

    dataservice.contact_point = contact_point_from_rdf(d, dataservice) or dataservice.contact_point

    for dataset_node in d.objects(DCAT.servesDataset):
        id = dataset_node.value(DCT.identifier)
        dataset = next((d for d in datasets if d is not None and d.harvest.remote_id == id), None)

        if dataset is None:
            # We try with `endswith` because Europe XSLT have problems with IDs. Sometimes they are prefixed with the domain of the catalog, sometimes not.
            dataset = next((d for d in datasets if d is not None and d.harvest.remote_id.endswith(id)), None)

        if dataset is not None:
            dataservice.datasets.append(dataset.id)

    license = rdf_value(d, DCT.license)
    if license is not None:
        dataservice.license = License.guess(license)

    dataservice.created_at = rdf_value(d, DCT.issued)
    dataservice.metadata_modified_at = rdf_value(d, DCT.modified)

    dataservice.tags = themes_from_rdf(d)

    return dataservice