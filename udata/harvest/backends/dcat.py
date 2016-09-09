# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from HTMLParser import HTMLParser

import html2text

from rdflib import Graph
from rdflib.namespace import Namespace, RDF, SKOS, FOAF, URIRef
from rdflib.util import SUFFIX_FORMAT_MAP, guess_format

from udata.rdf import DCAT, DCT, namespace_manager
from udata.models import db, Resource, License, SpatialCoverage
from udata.utils import get_by, daterange_start, daterange_end

from . import BaseBackend, register
from ..exceptions import HarvestException, HarvestSkipException

log = logging.getLogger(__name__)

RESOURCE_TYPES = ('file', 'file.upload', 'api', 'documentation',
                  'image', 'visualization')

ALLOWED_RESOURCE_TYPES = ('file', 'file.upload', 'api')


# Support JSON-LD in format detection
FORMAT_MAP = SUFFIX_FORMAT_MAP.copy()
FORMAT_MAP['json'] = 'json-ld'
FORMAT_MAP['jsonld'] = 'json-ld'


class HTMLDetector(HTMLParser):
    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self, *args, **kwargs)
        self.elements = set()

    def handle_starttag(self, tag, attrs):
        self.elements.add(tag)

    def handle_endtag(self, tag):
        self.elements.add(tag)


def is_html(text):
    parser = HTMLDetector()
    parser.feed(text)
    return bool(parser.elements)


@register
class DcatBackend(BaseBackend):
    name = 'dcat'
    display_name = 'DCAT'

    def initialize(self):
        '''List all datasets for a given ...'''
        fmt = guess_format(self.source.url, FORMAT_MAP)
        graph = Graph(namespace_manager=namespace_manager)
        graph.parse(self.source.url, format=fmt)
        for id, data in self.dcat_datasets(graph):
            self.add_item(id, graph=data)

    def dcat_datasets(self, graph):
        '''
        Extract DCAT dataset from a DCAT graph.
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
        dcat = list(graph.subjects(RDF.type, DCAT.Dataset))[0]
        dataset = self.get_dataset(item.remote_id)

        # # Skip if no resource
        # if not len(data.get('resources', [])):
        #     msg = 'Dataset {0} has no record'.format(item.remote_id)
        #     raise HarvestSkipException(msg)

        dataset.title = graph.value(dcat, DCT.title)
        description = graph.value(dcat, DCT.description) or ''
        if is_html(description):
            dataset.description = html2text.html2text(description.strip(),
                                                      bodywidth=0)
        else:
            dataset.description = description.strip()
        # dataset.license = License.objects(id=data['license_id']).first()
        # dataset.license = license or License.objects.get(id='notspecified')
        tags = list(graph.objects(dcat, DCAT.keyword))
        tags += list(graph.objects(dcat, DCAT.theme))
        dataset.tags = list(set(tags))
        #
        # dataset.created_at = data['issued']
        # dataset.last_modified = data['modified']
        #
        dataset.extras['dcat:identifier'] = item.remote_id
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
        # Resources
        for distrib in graph.objects(dcat, DCAT.distribution):
            download_url = graph.value(distrib, DCAT.downloadURL)
            access_url = graph.value(distrib, DCAT.accessURL)
            url = str(download_url or access_url)

            resource = get_by(dataset.resources, 'url', url)
            if not resource:
                resource = Resource()
                dataset.resources.append(resource)
            # if res['resource_type'] not in ALLOWED_RESOURCE_TYPES:
            #     continue
            resource.title = graph.value(distrib, DCT.title)
            resource.url = url
            description = graph.value(distrib, DCT.description) or ''
            if is_html(description):
                resource.description = html2text.html2text(description.strip(),
                                                           bodywidth=0)
            else:
                resource.description = description.strip()
            # resource.url = res['url']
            # resource.filetype = ('api' if res['resource_type'] == 'api'
            #                      else 'remote')
            # resource.format = res.get('format')
            # resource.mime = res.get('mimetype')
            # resource.hash = res.get('hash')
            # resource.created = res['created']
            # resource.modified = res['last_modified']
            # resource.published = resource.published or resource.created

        return dataset
