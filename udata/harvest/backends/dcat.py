import logging
from datetime import date
from typing import ClassVar, Generator

import lxml.etree as ET
from flask import current_app
from rdflib import Graph
from rdflib.namespace import RDF
from typing_extensions import override

from udata.core.dataservices.rdf import dataservice_from_rdf
from udata.core.dataset.rdf import dataset_from_rdf
from udata.harvest.models import HarvestError, HarvestItem
from udata.i18n import gettext as _
from udata.rdf import (
    DCAT,
    DCT,
    HYDRA,
    SPDX,
    guess_format,
    namespace_manager,
    rdf_value,
    url_from_rdf,
)
from udata.storage.s3 import store_as_json

from .base import BaseBackend, HarvestExtraConfig

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
OWS_NAMESPACE = "http://www.opengis.net/ows"

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
    display_name = "DCAT"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organizations_to_update = set()

    def inner_harvest(self):
        fmt = self.get_format()
        self.job.data = {"format": fmt}

        pages = []

        for page_number, page in self.walk_graph(self.source.url, fmt):
            self.process_one_datasets_page(page_number, page)
            pages.append((page_number, page))

        for org in self.organizations_to_update:
            org.compute_aggregate_metrics = True
            org.count_datasets()

        # We do a second pass to have all datasets in memory and attach datasets
        # to dataservices. It could be better to be one pass of graph walking and
        # then one pass of attaching datasets to dataservices.
        for page_number, page in pages:
            self.process_one_dataservices_page(page_number, page)

        if not self.dryrun and self.has_reached_max_items():
            # We have reached the max_items limit. Warn the user that all the datasets may not be present.
            error = HarvestError(
                message=f"{self.max_items} max items reached, not all datasets/dataservices were retrieved"
            )
            self.job.errors.append(error)

        # The official MongoDB document size in 16MB. The default value here is 15MB to account for other fields in the document (and for difference between * 1024 vs * 1000).
        max_harvest_graph_size_in_mongo = current_app.config.get(
            "HARVEST_MAX_CATALOG_SIZE_IN_MONGO"
        )
        if max_harvest_graph_size_in_mongo is None:
            max_harvest_graph_size_in_mongo = 15 * 1000 * 1000

        bucket = current_app.config.get("HARVEST_GRAPHS_S3_BUCKET")

        serialized_graphs = [p.serialize(format=fmt, indent=None) for _, p in pages]

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

    def get_format(self):
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

    def walk_graph(self, url: str, fmt: str) -> Generator[tuple[int, Graph], None, None]:
        """
        Yield all RDF pages as `Graph` from the source
        """
        page_number = 0
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

            yield page_number, subgraph
            if self.has_reached_max_items():
                return

            page_number += 1

    def process_one_datasets_page(self, page_number: int, page: Graph):
        for node in page.subjects(RDF.type, DCAT.Dataset):
            remote_id = page.value(node, DCT.identifier)
            if self.is_dataset_external_to_this_page(page, node):
                continue

            self.process_dataset(remote_id, page_number=page_number, page=page, node=node)

            if self.has_reached_max_items():
                return

    def is_dataset_external_to_this_page(self, page: Graph, node) -> bool:
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
        resource = page.resource(node)
        title = rdf_value(resource, DCT.title)
        if title:
            return False

        predicates = [link_type for (_other_node, link_type) in page.subject_predicates(node)]
        return len(predicates) == 1 and (
            predicates[0] == DCAT.servesDataset or predicates[0] == DCT.hasPart
        )

    def process_one_dataservices_page(self, page_number: int, page: Graph):
        access_services = {o for _, _, o in page.triples((None, DCAT.accessService, None))}
        for node in page.subjects(RDF.type, DCAT.DataService):
            if node in access_services:
                continue
            remote_id = page.value(node, DCT.identifier)
            self.process_dataservice(remote_id, page_number=page_number, page=page, node=node)

            if self.has_reached_max_items():
                return

    def inner_process_dataset(self, item: HarvestItem, page_number: int, page: Graph, node):
        item.kwargs["page_number"] = page_number

        dataset = self.get_dataset(item.remote_id)
        remote_url_prefix = self.get_extra_config_value("remote_url_prefix")
        dataset = dataset_from_rdf(page, dataset, node=node, remote_url_prefix=remote_url_prefix)
        if dataset.organization:
            dataset.organization.compute_aggregate_metrics = False
            self.organizations_to_update.add(dataset.organization)
        return dataset

    def inner_process_dataservice(self, item: HarvestItem, page_number: int, page: Graph, node):
        item.kwargs["page_number"] = page_number

        dataservice = self.get_dataservice(item.remote_id)
        remote_url_prefix = self.get_extra_config_value("remote_url_prefix")
        return dataservice_from_rdf(
            page,
            dataservice,
            node,
            [item.dataset for item in self.job.items],
            remote_url_prefix=remote_url_prefix,
        )

    def get_node_from_item(self, graph, item):
        for node in graph.subjects(RDF.type, DCAT.Dataset):
            if str(graph.value(node, DCT.identifier)) == item.remote_id:
                return node
        raise ValueError(f"Unable to find dataset with DCT.identifier:{item.remote_id}")


class CswDcatBackend(DcatBackend):
    """
    CSW harvester fetching records as DCAT.
    The parsing of items is then the same as for the DcatBackend.
    """

    display_name = "CSW-DCAT"

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

    CSW_OUTPUT_SCHEMA = "http://www.w3.org/ns/dcat#"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.xml_parser = ET.XMLParser(resolve_entities=False)

    def walk_graph(self, url: str, fmt: str) -> Generator[tuple[int, Graph], None, None]:
        """
        Yield all RDF pages as `Graph` from the source
        """
        page_number = 0
        start = 1

        while True:
            data = self.CSW_REQUEST.format(output_schema=self.CSW_OUTPUT_SCHEMA, start=start)
            response = self.post(url, data=data, headers={"Content-Type": "application/xml"})
            response.raise_for_status()

            content = response.content
            tree = ET.fromstring(content, parser=self.xml_parser)
            if tree.tag == "{" + OWS_NAMESPACE + "}ExceptionReport":
                raise ValueError(f"Failed to query CSW:\n{content}")

            search_results = tree.find("csw:SearchResults", {"csw": CSW_NAMESPACE})
            if not search_results:
                log.error(f"No search results found for {url} on page {page_number}")
                return

            for result in search_results:
                subgraph = Graph(namespace_manager=namespace_manager)
                doc = ET.tostring(self.as_dcat(result))
                subgraph.parse(data=doc, format=fmt)

                if not subgraph.subjects(
                    RDF.type, [DCAT.Dataset, DCAT.DatasetSeries, DCAT.DataService]
                ):
                    raise ValueError("Failed to fetch CSW content")

                yield page_number, subgraph

                if self.has_reached_max_items():
                    return

            page_number += 1
            start = self.next_position(start, search_results)
            if not start:
                return

    def as_dcat(self, tree: ET._Element) -> ET._Element:
        """
        Return the input tree as a DCAT tree.
        For CswDcatBackend, this method return the incoming tree as-is, since it's already DCAT.
        For subclasses of CswDcatBackend, this method should convert the incoming tree to DCAT.
        """
        return tree

    def next_position(self, start: int, search_results: ET._Element) -> int | None:
        next_record = int(search_results.attrib["nextRecord"])
        matched_count = int(search_results.attrib["numberOfRecordsMatched"])
        returned_count = int(search_results.attrib["numberOfRecordsReturned"])

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
            # Enough items have been harvested already
            or self.has_reached_max_items()
        )
        return None if should_break else next_record


class CswIso19139DcatBackend(CswDcatBackend):
    """
    CSW harvester fetching records as ISO-19139 and using XSLT to convert them to DCAT.
    The parsing of items is then the same as for the DcatBackend.
    """

    display_name = "CSW-ISO-19139"

    extra_configs = (
        HarvestExtraConfig(
            _("Remote URL prefix"),
            "remote_url_prefix",
            str,
            _("A prefix used to build the remote URL of the harvested items."),
        ),
    )

    CSW_OUTPUT_SCHEMA = "http://www.isotc211.org/2005/gmd"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        xslt_url = current_app.config["HARVEST_ISO19139_XSLT_URL"]
        xslt = ET.fromstring(self.get(xslt_url).content, parser=self.xml_parser)
        self.transform = ET.XSLT(xslt)

    @override
    def as_dcat(self, tree: ET._Element) -> ET._Element:
        return self.transform(tree, CoupledResourceLookUp="'disabled'")
