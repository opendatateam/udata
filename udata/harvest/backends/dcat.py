# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from rdflib import Graph
from rdflib.namespace import RDF

from udata.rdf import DCAT, DCT, SPDX, namespace_manager, guess_format
from udata.models import db, Resource, License, SpatialCoverage
from udata.core.dataset.rdf import dataset_from_rdf
from udata.utils import get_by, daterange_start, daterange_end

from . import BaseBackend, register
from ..exceptions import HarvestException, HarvestSkipException

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


def extract_graph(source, target, node, specs):
    for p, o in source.predicate_objects(node):
        target.add((node, p, o))
        if p in specs:
            extract_graph(source, target, o, specs[p])


@register
class DcatBackend(BaseBackend):
    name = 'dcat'
    display_name = 'DCAT'

    def initialize(self):
        '''List all datasets for a given ...'''
        fmt = guess_format(self.source.url)
        graph = Graph(namespace_manager=namespace_manager)
        graph.parse(self.source.url, format=fmt)
        for id, data in self.dcat_datasets(graph):
            self.add_item(id, graph=data)

    def dcat_datasets(self, graph):
        '''
        Extract DCAT dataset from a RDF graph.
        '''
        for node in graph.subjects(RDF.type, DCAT.Dataset):
            dcat_id = graph.value(node, DCT.identifier)
            subgraph = Graph(namespace_manager=namespace_manager)
            extract_graph(graph, subgraph, node, DCAT_NESTING)
            yield str(dcat_id), subgraph.serialize(format='json-ld',
                                                   indent=None)

    def process(self, item):
        graph = Graph(namespace_manager=namespace_manager)
        graph.parse(data=item.kwargs['graph'], format='json-ld')
        dataset = self.get_dataset(item.remote_id)
        dataset = dataset_from_rdf(graph, dataset)
        # # Skip if no resource
        # if not len(data.get('resources', [])):
        #     msg = 'Dataset {0} has no record'.format(item.remote_id)
        #     raise HarvestSkipException(msg)
    #
    #     spatial_geom = None
    #
    #     for extra in data['extras']:
    #         # GeoJSON representation (Polygon or Point)
    #         if extra['key'] == 'spatial':
    #             spatial_geom = json.loads(extra['value'])
    #         #  Textual representation of the extent / location
    #         elif extra['key'] == 'spatial-text':
    #             log.debug('spatial-text value not handled')
    #             print 'spatial-text', extra['value']
    #         # Linked Data URI representing the place name
    #         elif extra['key'] == 'spatial-uri':
    #             log.debug('spatial-uri value not handled')
    #             print 'spatial-uri', extra['value']
    #         # Update frequency
    #         elif extra['key'] == 'frequency':
    #             print 'frequency', extra['value']
    #         # else:
    #         #     print extra['key'], extra['value']
    #         dataset.extras[extra['key']] = extra['value']
    #
    #     if spatial_geom:
    #         dataset.spatial = SpatialCoverage()
    #         if spatial_geom['type'] == 'Polygon':
    #             coordinates = [spatial_geom['coordinates']]
    #         elif spatial_geom['type'] == 'MultiPolygon':
    #             coordinates = spatial_geom['coordinates']
    #         else:
    #             HarvestException('Unsupported spatial geometry')
    #         dataset.spatial.geom = {
    #             'type': 'MultiPolygon',
    #             'coordinates': coordinates
    #         }
    #
    #     if temporal_start and temporal_end:
    #         dataset.temporal_coverage = db.DateRange(
    #             start=temporal_start,
    #             end=temporal_end,
    #         )
    #
    #     # Remote URL
    #     if data.get('url'):
    #         dataset.extras['remote_url'] = data['url']
    #

        return dataset
