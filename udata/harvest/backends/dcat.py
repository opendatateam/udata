import logging
import traceback
from abc import ABC, abstractmethod
from datetime import date
from typing import ClassVar, Generator

from flask import current_app
from rdflib import Graph, Node
from rdflib.namespace import RDF
from saxonche import PySaxonProcessor, PyXdmNode
from typing_extensions import override
from werkzeug.utils import cached_property

from udata.core.dataservices.models import Dataservice
from udata.core.dataservices.rdf import dataservice_from_rdf
from udata.core.dataset.models import Dataset
from udata.core.dataset.rdf import dataset_from_rdf
from udata.harvest.models import HarvestError, HarvestItem
from udata.i18n import lazy_gettext as _
from udata.rdf import (
    DCAT,
    DCT,
    GEODCAT,
    HYDRA,
    SPDX,
    guess_format,
    namespace_manager,
    rdf_value,
    url_from_rdf,
)
from udata.storage.s3 import store_as_json
from udata.utils import safe_unicode, uniquify

from .base import BaseBackend, HarvestExtraConfig, HarvestFeature

log = logging.getLogger(__name__)


# Attributes representing nested classes to be stored in the graph
# in order to have a complete graph
DCAT_NESTING = {
    DCAT.distribution: {SPDX.checksum: {}},
    DCT.temporal: {},
    DCT.spatial: {},
}

# Fix some misnamed properties
DCAT_NESTING[DCAT.distributions] = DCAT_NESTING[DCAT.distribution]

# Known pagination class and their next page property
KNOWN_PAGINATION = (
    (HYDRA.PartialCollectionView, HYDRA.next),
    (HYDRA.PagedCollection, HYDRA.nextPage),
)

CSW_NAMESPACE = "http://www.opengis.net/cat/csw/2.0.2"

# Useful to patch essential failing URIs
URIS_TO_REPLACE = {
    # See https://github.com/etalab/data.gouv.fr/issues/1151
    "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld": "https://gist.githubusercontent.com/maudetes/f019586185d6f59dcfb07f97148a1973/raw/585c3c7bf602b5a4e635b137257d0619792e2c1f/gistfile1.txt"  # noqa
}


def extract_graph(source, target, node, specs):
    for p, o in source.predicate_objects(node):
        target.add((node, p, o))
        if p in specs:
            extract_graph(source, target, o, specs[p])


class DcatBackend(BaseBackend):
    name = "dcat"
    display_name = "DCAT"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graphs = list[tuple[Graph, int]]()

    @override
    def inner_harvest(self):
        self.job.data = {"format": self.format}

        for page_graph, page_number in self.walk_paginated_graph(self.source.url):
            self.process_one_datasets_page(page_graph, page_number)
            self.graphs.append((page_graph, page_number))

        # We do a second pass to have all datasets in memory and attach datasets
        # to dataservices. It could be better to be one pass of graph walking and
        # then one pass of attaching datasets to dataservices.
        for page_graph, page_number in self.graphs:
            self.process_one_dataservices_page(page_graph, page_number)

    @override
    def inner_end_job(self):
        self.store_graphs()

    @cached_property
    def format(self) -> str:
        fmt = guess_format(self.source.url)
        # if format can't be guessed from the url
        # we fallback on the declared Content-Type
        if not fmt:
            response = self.head(self.source.url)
            response.raise_for_status()
            mime_type = response.headers.get("Content-Type", "").split(";", 1)[0]
            if not mime_type:
                msg = "Unable to detect format from extension or mime type"
                raise ValueError(msg)
            fmt = guess_format(mime_type)
            if not fmt:
                msg = 'Unsupported mime type "{0}"'.format(mime_type)
                raise ValueError(msg)
        return fmt

    def walk_paginated_graph(self, url: str) -> Generator[tuple[Graph, int], None, None]:
        """
        Yield each RDF page from the source as a separate `Graph`.
        """
        page_number = 0
        while url:
            page_graph = Graph(namespace_manager=namespace_manager)
            response = self.get(url)
            response.raise_for_status()
            data = response.text
            for old_uri, new_uri in URIS_TO_REPLACE.items():
                data = data.replace(old_uri, new_uri)
            page_graph.parse(data=data, format=self.format)

            url = None
            for cls, prop in KNOWN_PAGINATION:
                if (None, RDF.type, cls) in page_graph:
                    pagination = page_graph.value(predicate=RDF.type, object=cls)
                    pagination = page_graph.resource(pagination)
                    url = url_from_rdf(pagination, prop)
                    break

            yield page_graph, page_number
            page_number += 1

    def process_one_datasets_page(self, graph: Graph, page_number: int):
        # Manually deduplicate subjects to ensure a node is only processed once.
        # Rdflib subjects() will return the same node multiple times if it matches different types,
        # which can occur with ISO series converted by SEMIC (by default it sets rdf:type to both
        # Dataset and DatasetSeries).
        for node in uniquify(graph.subjects(RDF.type, [DCAT.Dataset, DCAT.DatasetSeries])):
            if self.is_dataset_external_to_this_graph(node, graph):
                continue

            remote_id = str(v) if (v := graph.value(node, DCT.identifier)) else None
            self.process_item(
                remote_id, self.process_dataset, node=node, graph=graph, page_number=page_number
            )

    def process_one_dataservices_page(self, graph: Graph, page_number: int):
        access_services = {o for _, _, o in graph.triples((None, DCAT.accessService, None))}

        for node in graph.subjects(RDF.type, DCAT.DataService):
            if node in access_services:
                continue

            remote_id = str(v) if (v := graph.value(node, DCT.identifier)) else None
            self.process_item(
                remote_id, self.process_dataservice, node=node, graph=graph, page_number=page_number
            )

    def is_dataset_external_to_this_graph(self, node: Node, graph: Graph) -> bool:
        # In dataservice nodes we have `servesDataset` or `hasPart` that can contains nodes
        # with type=dataset. We don't want to process them because these nodes are empty (they
        # only contains a link to the dataset definition).
        # These datasets are either present in the catalog in previous or next pages or
        # external from the catalog we are currently harvesting (so we don't want to harvest them).
        # First we thought of skipping them inside `dataset_from_rdf` (see :ExcludeExternalyDefinedDataset)
        # but it creates a lot of "fake" items in the job and raising problems (reaching the max harvest item for
        # example and not getting to the "real" datasets/dataservices in subsequent pages)
        # So to prevent creating a lot of useless items in the job we first thought about checking to see if there is no title and
        # if `isPrimaryTopicOf` is present. But it may be better to check if the only link of the node with the current page is a
        # `servesDataset` or `hasPart`. If it's the case, the node is only present in a dataservice. (maybe we could also check that
        # the `_other_node` is a dataservice?)
        # `isPrimaryTopicOf` is the tag present in the first harvester raising the problem, it may exists other
        # values of the same sort we need to check here.

        # This is not dangerous because we check for missing title in `dataset_from_rdf` later so we would have skipped
        # this dataset anyway.
        resource = graph.resource(node)
        title = rdf_value(resource, DCT.title)
        if title:
            return False

        predicates = [link_type for (_, link_type) in graph.subject_predicates(node)]
        return len(predicates) == 1 and (
            predicates[0] == DCAT.servesDataset or predicates[0] == DCT.hasPart
        )

    def process_dataset(
        self,
        harvest_item: HarvestItem,
        node: Node,
        graph: Graph,
        page_number: int,
    ) -> Dataset:
        harvest_item.kwargs["page_number"] = page_number
        remote_url_prefix = self.get_extra_config_value("remote_url_prefix")

        dataset = self.get_item(harvest_item.remote_id, Dataset)
        dataset = dataset_from_rdf(
            graph, dataset, node=node, remote_url_prefix=remote_url_prefix, dryrun=self.dryrun
        )

        return dataset

    def process_dataservice(
        self,
        harvest_item: HarvestItem,
        node: Node,
        graph: Graph,
        page_number: int,
    ) -> Dataservice:
        harvest_item.kwargs["page_number"] = page_number
        remote_url_prefix = self.get_extra_config_value("remote_url_prefix")

        dataservice = self.get_item(harvest_item.remote_id, Dataservice)
        dataservice = dataservice_from_rdf(
            graph,
            dataservice,
            node,
            [itm.dataset for itm in self.job.items],
            remote_url_prefix=remote_url_prefix,
            dryrun=self.dryrun,
        )

        return dataservice

    def store_graphs(self):
        # The official MongoDB document size in 16MB. The default value here is 15MB to account
        # for other fields in the document (and for difference between * 1024 vs * 1000).
        max_harvest_graph_size_in_mongo = current_app.config.get(
            "HARVEST_MAX_CATALOG_SIZE_IN_MONGO"
        )
        if max_harvest_graph_size_in_mongo is None:
            max_harvest_graph_size_in_mongo = 15 * 1000 * 1000

        bucket = current_app.config.get("HARVEST_GRAPHS_S3_BUCKET")

        serialized_graphs = [g.serialize(format=self.format, indent=None) for g, _ in self.graphs]

        if (
            bucket is not None
            and sum([len(g.encode("utf-8")) for g in serialized_graphs])
            >= max_harvest_graph_size_in_mongo
        ):
            prefix = current_app.config.get("HARVEST_GRAPHS_S3_FILENAME_PREFIX") or ""

            # TODO: we could store each page in independant files to allow downloading only the require page in
            # subsequent jobs. (less data to download in each job)
            filename = f"{prefix}harvest_{self.job.id}_{date.today()}.json"

            store_as_json(bucket, filename, serialized_graphs)

            self.job.data["filename"] = filename
        else:
            self.job.data["graphs"] = serialized_graphs

    def get_node_from_item(self, graph, item):
        for node in graph.subjects(RDF.type, DCAT.Dataset):
            if str(graph.value(node, DCT.identifier)) == item.remote_id:
                return node
        raise ValueError(f"Unable to find dataset with DCT.identifier:{item.remote_id}")


class BaseCswDcatBackend(DcatBackend, ABC):
    """
    Abstract base CSW to DCAT harvester.

    Once items are retrieved from CSW, the parsing of these items is the same as DcatBackend.
    """

    extra_configs = (
        HarvestExtraConfig(
            _("Remote URL prefix"),
            "remote_url_prefix",
            str,
            _("A prefix used to build the remote URL of the harvested items."),
        ),
    )

    # CSW_REQUEST is based on:
    # - Request syntax from spec [1] and example requests [1] [2].
    # - Sort settings to ensure stable paging [3].
    # - Filter settings to only retrieve record types currently mapped in udata.
    #
    # If you modify the request, make sure:
    # - `typeNames` and `outputSchema` are consistent. You'll likely want to keep "gmd:MD_Metadata",
    #   since "csw:Record" contains less information.
    # - `typeNames` and namespaces in `csw:Query` (`Filter`, `SortBy`, ...) are consistent, although
    #   they are ignored on some servers [4] [5].
    # - It works on real catalogs! Not many servers implement the whole spec.
    #
    # References:
    # [1] OpenGIS Catalogue Services Specification 2.0.2 – ISO Metadata Application Profile: Corrigendum
    #     https://portal.ogc.org/files/80534
    # [2] GeoNetwork - CSW test requests
    #     https://github.com/geonetwork/core-geonetwork/tree/3.10.4/web/src/main/webapp/xml/csw/test
    # [3] Udata - Support csw dcat harvest
    #     https://github.com/opendatateam/udata/pull/2800#discussion_r1129053500
    # [4] GeoNetwork - GetRecords ignores namespaces for Filter/SortBy fields
    #     https://github.com/geonetwork/core-geonetwork/blob/3.10.4/csw-server/src/main/java/org/fao/geonet/kernel/csw/services/getrecords/FieldMapper.java#L92
    # [5] GeoNetwork - GetRecords ignores `typeNames`
    #     https://github.com/geonetwork/core-geonetwork/blob/3.10.4/csw-server/src/main/java/org/fao/geonet/kernel/csw/services/getrecords/CatalogSearcher.java#L194
    CSW_REQUEST: ClassVar[str] = """
    <csw:GetRecords xmlns:apiso="http://www.opengis.net/cat/csw/apiso/1.0"
                    xmlns:csw="http://www.opengis.net/cat/csw/2.0.2"
                    xmlns:ogc="http://www.opengis.net/ogc"
                    xmlns:gmd="http://www.isotc211.org/2005/gmd"
                    service="CSW" version="2.0.2" outputFormat="application/xml"
                    resultType="results" startPosition="{start}" maxRecords="25"
                    outputSchema="{output_schema}">
      <csw:Query typeNames="gmd:MD_Metadata">
        <csw:ElementSetName>full</csw:ElementSetName>
        <csw:Constraint version="1.1.0">
          <ogc:Filter>
            <ogc:Or>
              <ogc:PropertyIsEqualTo>
                <ogc:PropertyName>apiso:type</ogc:PropertyName>
                <ogc:Literal>dataset</ogc:Literal>
              </ogc:PropertyIsEqualTo>
              <ogc:PropertyIsEqualTo>
                <ogc:PropertyName>apiso:type</ogc:PropertyName>
                <ogc:Literal>nonGeographicDataset</ogc:Literal>
              </ogc:PropertyIsEqualTo>
              <ogc:PropertyIsEqualTo>
                <ogc:PropertyName>apiso:type</ogc:PropertyName>
                <ogc:Literal>series</ogc:Literal>
              </ogc:PropertyIsEqualTo>
              <ogc:PropertyIsEqualTo>
                <ogc:PropertyName>apiso:type</ogc:PropertyName>
                <ogc:Literal>service</ogc:Literal>
              </ogc:PropertyIsEqualTo>
            </ogc:Or>
          </ogc:Filter>
        </csw:Constraint>
        <ogc:SortBy>
          <ogc:SortProperty>
            <ogc:PropertyName>apiso:identifier</ogc:PropertyName>
            <ogc:SortOrder>ASC</ogc:SortOrder>
          </ogc:SortProperty>
        </ogc:SortBy>
      </csw:Query>
    </csw:GetRecords>
    """

    SAXON_SECURITY_FEATURES = {
        "http://saxon.sf.net/feature/allow-external-functions": "false",
        "http://saxon.sf.net/feature/parserFeature?uri=http://apache.org/xml/features/nonvalidating/load-external-dtd": "false",
        "http://saxon.sf.net/feature/parserFeature?uri=http://xml.org/sax/features/external-general-entities": "false",
        "http://saxon.sf.net/feature/parserFeature?uri=http://xml.org/sax/features/external-parameter-entities": "false",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saxon_proc = PySaxonProcessor(license=False)
        for feature, value in self.SAXON_SECURITY_FEATURES.items():
            self.saxon_proc.set_configuration_property(feature, value)
        self.saxon_proc.set_configuration_property(
            "http://saxon.sf.net/feature/strip-whitespace", "all"
        )
        self.xpath_proc = self.saxon_proc.new_xpath_processor()
        self.xpath_proc.declare_namespace("csw", CSW_NAMESPACE)

    @property
    @abstractmethod
    def output_schema(self) -> str:
        """
        Return the CSW `outputSchema` property.
        """
        pass

    @abstractmethod
    def as_dcat(self, tree: PyXdmNode) -> PyXdmNode:
        """
        Return the input tree as a DCAT tree.
        """
        pass

    @property
    @override
    def format(self) -> str:
        return "xml"

    @override
    def walk_paginated_graph(self, url: str) -> Generator[tuple[Graph, int], None, None]:
        """
        Yield all RDF pages as `Graph` from the source.
        """
        output_schema = self.output_schema
        page_number = 0
        start = 1

        while True:
            log.debug(f"Requesting CSW from start={start}")
            data = self.CSW_REQUEST.format(output_schema=output_schema, start=start)
            response = self.post(url, data=data, headers={"Content-Type": "application/xml"})
            response.raise_for_status()

            text = response.text
            tree = self.saxon_proc.parse_xml(xml_text=text)
            self.xpath_proc.set_context(xdm_item=tree)

            # Using * namespace so we don't have to enumerate ows versions
            if self.xpath_proc.evaluate("/*:ExceptionReport"):
                raise ValueError(f"Failed to query CSW:\n{text}")

            if r := self.xpath_proc.evaluate("/csw:GetRecordsResponse/csw:SearchResults"):
                search_results = r.head
            else:
                log.error(f"No search results found for {url} on page {page_number}")
                return

            for result in search_results.children:
                if result.node_kind_str != "element":
                    # Saxonche returns all children, including comments and other non-element nodes
                    continue
                page_graph = Graph(namespace_manager=namespace_manager)
                try:
                    doc = self.as_dcat(result).to_string("utf-8")
                    page_graph.parse(data=doc, format=self.format)
                except Exception as e:
                    # Record the original XML even when as_dcat() succeeds, because the conversion
                    # might lose some information needed to understand the problem.
                    xml = result.to_string("utf-8")
                    log.error(f"Error parsing source record: {e}\nSource XML: {xml}")
                    self.add_harvest_item(
                        HarvestItem(
                            status="failed",
                            errors=[
                                HarvestError(
                                    message=safe_unicode(e),
                                    details=f"Source XML: {xml}\n{traceback.format_exc()}",
                                )
                            ],
                        )
                    )
                    continue

                if not page_graph.subjects(
                    RDF.type, [DCAT.Dataset, DCAT.DatasetSeries, DCAT.DataService]
                ):
                    raise ValueError("Failed to fetch CSW content")

                yield page_graph, page_number

            page_number += 1
            start = self._next_position(start, search_results)
            if not start:
                return

    def _next_position(self, start: int, search_results: PyXdmNode) -> int | None:
        next_record = int(search_results.get_attribute_value("nextRecord"))
        matched_count = int(search_results.get_attribute_value("numberOfRecordsMatched"))
        returned_count = int(search_results.get_attribute_value("numberOfRecordsReturned"))

        # Break conditions copied gratefully from
        # noqa https://github.com/geonetwork/core-geonetwork/blob/main/harvesters/src/main/java/org/fao/geonet/kernel/harvest/harvester/csw/Harvester.java#L338-L369
        should_break = (
            # A value of 0 means all records have been returned (standard CSW)
            (next_record == 0)
            # Misbehaving CSW server returning a next record > matched count
            or (next_record > matched_count)
            # No results returned already
            or (returned_count == 0)
            # Current next record is lower than previous one
            or (next_record < start)
        )
        return None if should_break else next_record


class CswDcatBackend(BaseCswDcatBackend):
    """
    CSW harvester fetching records as DCAT.
    """

    name = "csw-dcat"
    display_name = "CSW-DCAT"

    features = (
        *BaseCswDcatBackend.features,
        HarvestFeature(
            "geodcatap",
            _("GeoDCAT-AP"),
            _("Request GeoDCAT-AP to the CSW server (must be supported by the server)."),
            default=False,
        ),
    )

    @property
    @override
    def output_schema(self) -> str:
        return GEODCAT if self.has_feature("geodcatap") else DCAT

    @override
    def as_dcat(self, tree: PyXdmNode) -> PyXdmNode:
        return tree


class CswIso19139DcatBackend(BaseCswDcatBackend):
    """
    CSW harvester fetching records as ISO-19139 and using XSLT to convert them to DCAT.
    """

    name = "csw-iso-19139"
    display_name = "CSW-ISO-19139"

    xslt_params = {
        "CoupledResourceLookUp": "disabled",
        "include-deprecated": "yes",  # required for dct:rights
        "locale-preferred-lang": "fre",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        xslt_url = current_app.config["HARVEST_ISO19139_XSLT_URL"]
        xslt_text = self.get(xslt_url).text
        xslt_proc = self.saxon_proc.new_xslt30_processor()
        self.xslt_exec = xslt_proc.compile_stylesheet(stylesheet_text=xslt_text)
        for key, value in self.xslt_params.items():
            self.xslt_exec.set_parameter(key, self.saxon_proc.make_string_value(value))

    @property
    @override
    def output_schema(self) -> str:
        return "http://www.isotc211.org/2005/gmd"

    @override
    def as_dcat(self, tree: PyXdmNode) -> PyXdmNode:
        return self.xslt_exec.transform_to_value(xdm_node=tree).head
