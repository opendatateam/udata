import logging

import requests

from rdflib import Graph, URIRef, BNode
from rdflib.namespace import RDF

from udata.rdf import (
    DCAT, DCT, HYDRA, SPDX, namespace_manager, guess_format, url_from_rdf, CONTEXT
)
from udata.core.dataset.rdf import dataset_from_rdf

from .base import BaseBackend

log = logging.getLogger(__name__)


# Attributes representing nested classes to be stored in the graph
# in order to have a complete graph
DCAT_NESTING = {
    DCAT.distribution: {
        SPDX.checksum: {}
    },
    DCT.temporal: {},
    DCT.spatial: {},
}

# Fix some misnamed properties
DCAT_NESTING[DCAT.distributions] = DCAT_NESTING[DCAT.distribution]

# Known pagination class and their next page property
KNOWN_PAGINATION = (
    (HYDRA.PartialCollectionView, HYDRA.next),
    (HYDRA.PagedCollection, HYDRA.nextPage)
)


def extract_graph(source, target, node, specs):
    for p, o in source.predicate_objects(node):
        target.add((node, p, o))
        if p in specs:
            extract_graph(source, target, o, specs[p])


class DcatBackend(BaseBackend):
    display_name = 'DCAT'

    def initialize(self):
        '''List all datasets for a given ...'''
        fmt = guess_format(self.source.url)
        # if format can't be guessed from the url
        # we fallback on the declared Content-Type
        if not fmt:
            response = requests.head(self.source.url)
            mime_type = response.headers.get('Content-Type', '').split(';', 1)[0]
            if not mime_type:
                msg = 'Unable to detect format from extension or mime type'
                raise ValueError(msg)
            fmt = guess_format(mime_type)
            if not fmt:
                msg = 'Unsupported mime type "{0}"'.format(mime_type)
                raise ValueError(msg)
        graph = self.parse_graph(self.source.url, fmt)
        self.job.data = {'graph': graph.serialize(format='json-ld', indent=None)}

    def parse_graph(self, url, fmt):
        graph = Graph(namespace_manager=namespace_manager)
        while url:
            subgraph = Graph(namespace_manager=namespace_manager)
            subgraph.parse(data=requests.get(url).text, format=fmt)

            url = None
            for cls, prop in KNOWN_PAGINATION:
                if (None, RDF.type, cls) in subgraph:
                    pagination = subgraph.value(predicate=RDF.type, object=cls)
                    pagination = subgraph.resource(pagination)
                    url = url_from_rdf(pagination, prop)
                    break

            graph += subgraph

        for node in graph.subjects(RDF.type, DCAT.Dataset):
            id = graph.value(node, DCT.identifier)
            kwargs = {'nid': str(node)}
            kwargs['type'] = 'uriref' if isinstance(node, URIRef) else 'blank'
            self.add_item(id, **kwargs)

        return graph

    def process(self, item):
        graph = Graph(namespace_manager=namespace_manager)
        data = item.kwargs.get('graph', self.job.data['graph'])  # handles legacy graphs
        node = None

        graph.parse(data=bytes(data), format='json-ld')

        if 'nid' in item.kwargs and 'type' in item.kwargs:
            nid = item.kwargs['nid']
            node = URIRef(nid) if item.kwargs['type'] == 'uriref' else BNode(nid)

        dataset = self.get_dataset(item.remote_id)
        dataset = dataset_from_rdf(graph, dataset, node=node)
        return dataset
