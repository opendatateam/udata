
from datetime import datetime
from typing import Optional
from rdflib import RDF, Graph

from udata.core.dataservices.models import Dataservice, HarvestMetadata
from udata.core.dataset.models import License
from udata.core.dataset.rdf import sanitize_html
from udata.harvest.models import HarvestSource
from udata.rdf import DCAT, DCT, contact_point_from_rdf, rdf_value, theme_labels_from_rdf, themes_from_rdf, url_from_rdf


def dataservice_from_rdf(graph: Graph, dataservice: Optional[Dataservice] = None, node=None, source: Optional[HarvestSource] = None):
    '''
    Create or update a dataset from a RDF/DCAT graph
    '''
    dataservice = dataservice or Dataservice()

    if node is None:  # Assume first match is the only match
        node = graph.value(predicate=RDF.type, object=DCAT.DataService)

    d = graph.resource(node)

    dataservice.title = rdf_value(d, DCT.title)
    dataservice.description = sanitize_html(d.value(DCT.description) or d.value(DCT.abstract))

    dataservice.base_api_url = url_from_rdf(d, DCAT.endpointURL)
    dataservice.endpoint_description_url = url_from_rdf(d, DCAT.endpointDescription)

    dataservice.contact_point = contact_point_from_rdf(d, dataservice) or dataservice.contact_point

    license = rdf_value(d, DCT.license)
    if license is not None:
        dataservice.license = License.guess(license)

    dataservice.created_at = rdf_value(d, DCT.issued)
    dataservice.metadata_modified_at = rdf_value(d, DCT.modified)

    dataservice.tags = themes_from_rdf(d)

    if not dataservice.harvest:
        dataservice.harvest = HarvestMetadata()

    if source is not None:
        dataservice.harvest.backend = source.backend

        dataservice.harvest.source_id = source.id
        dataservice.harvest.source_url = source.url

    dataservice.harvest.last_harvested_at = datetime.utcnow()

    return dataservice