# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from rdflib import Graph
from rdflib.namespace import RDF

from udata.rdf import DCAT, DCT, namespace_manager, guess_format
from udata.models import db, Resource, License, SpatialCoverage
from udata.core.dataset.rdf import dataset_from_rdf
from udata.utils import get_by, daterange_start, daterange_end

from . import BaseBackend, register
from ..exceptions import HarvestException, HarvestSkipException

log = logging.getLogger(__name__)


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
            subgraph += graph.triples((node, None, None))
            for distrib in graph.objects(node, DCAT.distribution):
                subgraph += graph.triples((distrib, None, None))
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
    #     temporal_start, temporal_end = None, None
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
    #         # Temporal coverage start
    #         elif extra['key'] == 'temporal_start':
    #             print 'temporal_start', extra['value']
    #             temporal_start = daterange_start(extra['value'])
    #             continue
    #         # Temporal coverage end
    #         elif extra['key'] == 'temporal_end':
    #             print 'temporal_end', extra['value']
    #             temporal_end = daterange_end(extra['value'])
    #             continue
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
