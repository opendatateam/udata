import logging

from rdflib import Graph, URIRef
from rdflib.namespace import RDF
import lxml.etree as ET
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
        self.job.data = {
            'graphs': [graph.serialize(format=fmt, indent=None) for graph in graphs],
            'format': fmt,
        }

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
        data = self.job.data['graphs'][item.kwargs['page']]
        format = self.job.data['format']

        graph.parse(data=bytes(data, encoding='utf8'), format=format)
        node = self.get_node_from_item(graph, item)

        dataset = self.get_dataset(item.remote_id)
        dataset = dataset_from_rdf(graph, dataset, node=node)
        return dataset


class CswDcatBackend(DcatBackend):
    display_name = 'CSW-DCAT'

    ISO_SCHEMA = 'http://www.isotc211.org/2005/gmd'

    def parse_graph(self, url: str, fmt: str) -> List[Graph]:
        '''
        Parse CSW graph querying ISO schema.
        Use GeoDCAT-AP XSLT to map it to a correct version.
        See https://github.com/SEMICeu/iso-19139-to-dcat-ap for more information on the XSLT.
        '''

        # Load XSLT
        xslURL = "https://raw.githubusercontent.com/SEMICeu/iso-19139-to-dcat-ap/master/iso-19139-to-dcat-ap.xsl"
        xsl = ET.fromstring(self.get(xslURL).content)
        transform = ET.XSLT(xsl)

        # Start querying and parsing graph
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
        page_size = 10
        response = self.post(url, data=body.format(start=start, schema=self.ISO_SCHEMA),
                             headers=headers)
        response.raise_for_status()
        xml = ET.fromstring(response.content)
        tree = transform(xml)

        while tree:
            subgraph = Graph(namespace_manager=namespace_manager)
            subgraph.parse(data = ET.tostring(tree), format=fmt)

            if not subgraph.subjects(RDF.type, DCAT.Dataset):
                raise ValueError("Failed to fetch CSW content")

            dataset_found = False
            for node in subgraph.subjects(RDF.type, DCAT.Dataset):
                id = subgraph.value(node, DCT.identifier)
                kwargs = {'nid': str(node), 'page': page}
                kwargs['type'] = 'uriref' if isinstance(node, URIRef) else 'blank'
                self.add_item(id, **kwargs)
                dataset_found = True

            if not dataset_found:
                break
            
            graphs.append(subgraph)
            page += 1
            start = start + page_size

            tree = transform(ET.fromstring(
                self.post(url, data=body.format(start=start, schema=self.ISO_SCHEMA),
                          headers=headers).content))

        return graphs
