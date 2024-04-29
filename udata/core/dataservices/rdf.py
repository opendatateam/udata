
from pprint import pprint
from typing import Optional
from rdflib import RDF, Graph
import rdflib
import lxml.etree as ET

from udata.core.dataservices.models import Dataservice
from udata.core.dataset.rdf import rdf_value, remote_url_from_rdf
from udata.rdf import DCAT, DCT, url_from_rdf


def dataservice_from_rdf(graph: Graph, dataservice: Optional[Dataservice] = None, node=None):
    '''
    Create or update a dataset from a RDF/DCAT graph
    '''
    dataservice = dataservice or Dataservice()

    if node is None:  # Assume first match is the only match
        node = graph.value(predicate=RDF.type, object=DCAT.DataService)

    d = graph.resource(node)

    dataservice.title = rdf_value(d, DCT.title)
    dataservice.base_api_url = rdf_value(d, DCAT.endpointURL)
    dataservice.endpoint_description_url = rdf_value(d, DCAT.endpointDescription)

    return dataservice