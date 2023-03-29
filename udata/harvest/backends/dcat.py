import logging

import requests

from rdflib import Graph, URIRef, BNode
from rdflib.namespace import RDF
from typing import List

from udata.rdf import (
    DCAT, DCT, HYDRA, SPDX, namespace_manager, guess_format, url_from_rdf
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
        fmt = self.get_format()
        graphs = self.parse_graph(self.source.url, fmt)
        self.job.data = {
            'graphs': [graph.serialize(format=fmt, indent=None) for graph in graphs],
            'format': fmt,
        }

    def get_format(self):
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
        return fmt

    def parse_graph(self, url, fmt) -> List[Graph]:
        """
        Returns an instance of rdflib.Graph for each detected page
        The index in the list is the page number
        """
        graphs = []
        page = 0
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
            graphs.append(subgraph)

            for node in subgraph.subjects(RDF.type, DCAT.Dataset):
                id = subgraph.value(node, DCT.identifier)
                kwargs = {'page': page}
                self.add_item(id, **kwargs)
                if self.max_items and len(self.job.items) >= self.max_items:
                    # this will stop iterating on pagination
                    url = None

            page += 1

        return graphs

    def get_node_from_item(self, graph, item):
        for node in graph.subjects(RDF.type, DCAT.Dataset):
            if str(graph.value(node, DCT.identifier)) == item.remote_id:
                return node
        raise ValueError(f'Unable to find dataset with DCT.identifier:{item.remote_id}')

    def process(self, item):
        graph = Graph(namespace_manager=namespace_manager)
        data = self.job.data['graphs'][item.kwargs['page']]
        format = self.job.data['format']

        graph.parse(data=bytes(data, encoding='utf8'), format=format)
        node = self.get_node_from_item(graph, item)

        dataset = self.get_dataset(item.remote_id)
        dataset = dataset_from_rdf(graph, dataset, node=node)
        return dataset
