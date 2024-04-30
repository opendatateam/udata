import logging

from rdflib import Graph, URIRef
from rdflib.namespace import RDF
import lxml.etree as ET
import boto3
from flask import current_app
from datetime import date
import json
from typing import List

from udata.rdf import (
    DCAT, DCT, HYDRA, SPDX, namespace_manager, guess_format, url_from_rdf
)
from udata.core.dataset.rdf import dataset_from_rdf
from udata.storage.s3 import store_as_json, get_from_json

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

CSW_NAMESPACE = 'http://www.opengis.net/cat/csw/2.0.2'
OWS_NAMESPACE = 'http://www.opengis.net/ows'

# Useful to patch essential failing URIs
URIS_TO_REPLACE = {
    # See https://github.com/etalab/data.gouv.fr/issues/1151
    'https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld': 'https://gist.githubusercontent.com/maudetes/f019586185d6f59dcfb07f97148a1973/raw/585c3c7bf602b5a4e635b137257d0619792e2c1f/gistfile1.txt'  # noqa
}


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

        self.job.data = { 'format': fmt }

        serialized_graphs = [graph.serialize(format=fmt, indent=None) for graph in graphs]

        # The official MongoDB document size in 16MB. The default value here is 15MB to account for other fields in the document (and for difference between * 1024 vs * 1000).
        max_harvest_graph_size_in_mongo = current_app.config.get('HARVEST_MAX_CATALOG_SIZE_IN_MONGO')
        if max_harvest_graph_size_in_mongo is None:
            max_harvest_graph_size_in_mongo = 15 * 1000 * 1000

        bucket = current_app.config.get('HARVEST_GRAPHS_S3_BUCKET')

        if bucket is not None and sum([len(g.encode('utf-8')) for g in serialized_graphs]) >= max_harvest_graph_size_in_mongo:
            prefix = current_app.config.get('HARVEST_GRAPHS_S3_FILENAME_PREFIX') or ''

            # TODO: we could store each page in independant files to allow downloading only the require page in
            # subsequent jobs. (less data to download in each job)
            filename = f'{prefix}harvest_{self.job.id}_{date.today()}.json'

            store_as_json(bucket, filename, serialized_graphs)

            self.job.data['filename'] = filename
        else:
            self.job.data['graphs'] = serialized_graphs

    def get_format(self):
        fmt = guess_format(self.source.url)
        # if format can't be guessed from the url
        # we fallback on the declared Content-Type
        if not fmt:
            response = self.head(self.source.url)
            response.raise_for_status()
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
            response = self.get(url)
            response.raise_for_status()
            data = response.text
            for old_uri, new_uri in URIS_TO_REPLACE.items():
                data = data.replace(old_uri, new_uri)
            subgraph.parse(data=data, format=fmt)

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
        if item.remote_id == 'None':
            raise ValueError('The DCT.identifier is missing on this DCAT.Dataset record')
        graph = Graph(namespace_manager=namespace_manager)

        if self.job.data.get('graphs') is not None:
            graphs = self.job.data['graphs']
        else:
            bucket = current_app.config.get('HARVEST_GRAPHS_S3_BUCKET')
            if bucket is None:
                raise ValueError(f"No bucket configured but the harvest job item {item.id} on job {self.job.id} doesn't have a graph in MongoDB.")

            graphs = get_from_json(bucket, self.job.data['filename'])
            if graphs is None:
                raise ValueError(f"The file '{self.job.data['filename']}' is missing in S3 bucket '{bucket}'")

        data = graphs[item.kwargs['page']]
        format = self.job.data['format']

        graph.parse(data=bytes(data, encoding='utf8'), format=format)
        node = self.get_node_from_item(graph, item)

        dataset = self.get_dataset(item.remote_id)
        dataset = dataset_from_rdf(graph, dataset, node=node)
        return dataset
    

    def next_record_if_should_continue(self, start, search_results):
        next_record = int(search_results.attrib['nextRecord'])
        matched_count = int(search_results.attrib['numberOfRecordsMatched'])
        returned_count = int(search_results.attrib['numberOfRecordsReturned'])

        # Break conditions copied gratefully from
        # noqa https://github.com/geonetwork/core-geonetwork/blob/main/harvesters/src/main/java/org/fao/geonet/kernel/harvest/harvester/csw/Harvester.java#L338-L369
        break_conditions = (
            # standard CSW: A value of 0 means all records have been returned.
            next_record == 0,

            # Misbehaving CSW server returning a next record > matched count
            next_record > matched_count,

            # No results returned already
            returned_count == 0,

            # Current next record is lower than previous one
            next_record < start,

            # Enough items have been harvested already
            self.max_items and len(self.job.items) >= self.max_items
        )

        if any(break_conditions):
            return None
        else:
            return next_record

class CswDcatBackend(DcatBackend):
    display_name = 'CSW-DCAT'

    DCAT_SCHEMA = 'http://www.w3.org/ns/dcat#'

    def parse_graph(self, url: str, fmt: str) -> List[Graph]:
        body = '''<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
                                  xmlns:gmd="http://www.isotc211.org/2005/gmd"
                                  service="CSW" version="2.0.2" resultType="results"
                                  startPosition="{start}" maxPosition="200"
                                  outputSchema="{schema}">
                    <csw:Query typeNames="gmd:MD_Metadata">
                        <csw:ElementSetName>full</csw:ElementSetName>
                        <ogc:SortBy xmlns:ogc="http://www.opengis.net/ogc">
                            <ogc:SortProperty>
                                <ogc:PropertyName>identifier</ogc:PropertyName>
                            <ogc:SortOrder>ASC</ogc:SortOrder>
                            </ogc:SortProperty>
                        </ogc:SortBy>
                    </csw:Query>
                </csw:GetRecords>'''
        headers = {'Content-Type': 'application/xml'}

        graphs = []
        page = 0
        start = 1

        response = self.post(url, data=body.format(start=start, schema=self.DCAT_SCHEMA),
                             headers=headers)
        response.raise_for_status()
        content = response.content
        tree = ET.fromstring(content)
        if tree.tag == '{' + OWS_NAMESPACE + '}ExceptionReport':
            raise ValueError(f'Failed to query CSW:\n{content}')
        while tree:
            graph = Graph(namespace_manager=namespace_manager)
            search_results = tree.find('csw:SearchResults', {'csw': CSW_NAMESPACE})
            if search_results is None:
                log.error(f'No search results found for {url} on page {page}')
                break
            for child in search_results:
                subgraph = Graph(namespace_manager=namespace_manager)
                subgraph.parse(data=ET.tostring(child), format=fmt)
                graph += subgraph

                for node in subgraph.subjects(RDF.type, DCAT.Dataset):
                    id = subgraph.value(node, DCT.identifier)
                    kwargs = {'nid': str(node), 'page': page}
                    kwargs['type'] = 'uriref' if isinstance(node, URIRef) else 'blank'
                    self.add_item(id, **kwargs)
            graphs.append(graph)

            next_record = self.next_record_if_should_continue(start, search_results)
            if not next_record:
                break

            start = next_record
            page += 1

            tree = ET.fromstring(
                self.post(url, data=body.format(start=start, schema=self.DCAT_SCHEMA),
                          headers=headers).content)

        return graphs


class CswIso19139DcatBackend(DcatBackend):
    '''
    An harvester that takes CSW ISO 19139 as input and transforms it to DCAT using SEMIC GeoDCAT-AP XSLT.
    The parsing of items is then the same as for the DcatBackend.
    '''

    display_name = 'CSW-ISO-19139'

    ISO_SCHEMA = 'http://www.isotc211.org/2005/gmd'

    XSL_URL = "https://raw.githubusercontent.com/SEMICeu/iso-19139-to-dcat-ap/master/iso-19139-to-dcat-ap.xsl"

    def parse_graph(self, url: str, fmt: str) -> List[Graph]:
        '''
        Parse CSW graph querying ISO schema.
        Use SEMIC GeoDCAT-AP XSLT to map it to a correct version.
        See https://github.com/SEMICeu/iso-19139-to-dcat-ap for more information on the XSLT.
        '''

        # Load XSLT
        xsl = ET.fromstring(self.get(self.XSL_URL).content)
        transform = ET.XSLT(xsl)

        # Start querying and parsing graph
        # Filter on dataset or serie records
        body = '''<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
                                  xmlns:gmd="http://www.isotc211.org/2005/gmd"
                                  service="CSW" version="2.0.2" resultType="results"
                                  startPosition="{start}" maxPosition="10"
                                  outputSchema="{schema}">
                      <csw:Query typeNames="csw:Record">
                        <csw:ElementSetName>full</csw:ElementSetName>
                        <csw:Constraint version="1.1.0">
                            <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
                                <ogc:Or xmlns:ogc="http://www.opengis.net/ogc">
                                    <ogc:PropertyIsEqualTo>
                                        <ogc:PropertyName>dc:type</ogc:PropertyName>
                                        <ogc:Literal>dataset</ogc:Literal>
                                    </ogc:PropertyIsEqualTo>
                                    <ogc:PropertyIsEqualTo>
                                        <ogc:PropertyName>dc:type</ogc:PropertyName>
                                        <ogc:Literal>series</ogc:Literal>
                                    </ogc:PropertyIsEqualTo>
                                </ogc:Or>
                            </ogc:Filter>
                        </csw:Constraint>
                    </csw:Query>
                </csw:GetRecords>'''
        headers = {'Content-Type': 'application/xml'}

        graphs = []
        page = 0
        start = 1

        response = self.post(url, data=body.format(start=start, schema=self.ISO_SCHEMA),
                             headers=headers)
        response.raise_for_status()

        tree_before_transform = ET.fromstring(response.content)
        # Disabling CoupledResourceLookUp to prevent failure on xlink:href
        # https://github.com/SEMICeu/iso-19139-to-dcat-ap/blob/master/documentation/HowTo.md#parameter-coupledresourcelookup
        tree = transform(tree_before_transform, CoupledResourceLookUp="'disabled'")

        while tree:
            # We query the tree before the transformation because the XSLT remove the search results
            # infos (useful for pagination)
            search_results = tree_before_transform.find('csw:SearchResults', {'csw': CSW_NAMESPACE})
            if search_results is None:
                log.error(f'No search results found for {url} on page {page}')
                break

            subgraph = Graph(namespace_manager=namespace_manager)
            subgraph.parse(ET.tostring(tree), format=fmt)

            if not subgraph.subjects(RDF.type, DCAT.Dataset):
                raise ValueError("Failed to fetch CSW content")

            for node in subgraph.subjects(RDF.type, DCAT.Dataset):
                id = subgraph.value(node, DCT.identifier)
                kwargs = {'nid': str(node), 'page': page}
                kwargs['type'] = 'uriref' if isinstance(node, URIRef) else 'blank'
                self.add_item(id, **kwargs)
            graphs.append(subgraph)

            next_record = self.next_record_if_should_continue(start, search_results)
            if not next_record:
                break

            start = next_record
            page += 1

            response = self.post(url, data=body.format(start=start, schema=self.ISO_SCHEMA),
                                 headers=headers)
            response.raise_for_status()

            tree_before_transform = ET.fromstring(response.content)
            tree = transform(tree_before_transform, CoupledResourceLookUp="'disabled'")

        return graphs
