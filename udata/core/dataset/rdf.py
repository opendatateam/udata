"""
This module centralize dataset helpers for RDF/DCAT serialization and parsing
"""

import calendar
import json
import logging
from datetime import date, datetime
from typing import Optional

from dateutil.parser import parse as parse_dt
from flask import current_app
from geomet import wkt
from mongoengine.errors import ValidationError
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF
from rdflib.resource import Resource as RdfResource

from udata import i18n, uris
from udata.core.dataset.models import HarvestDatasetMetadata, HarvestResourceMetadata
from udata.core.spatial.models import SpatialCoverage
from udata.harvest.exceptions import HarvestSkipException
from udata.models import db
from udata.rdf import (
    ADMS,
    CONTACT_POINT_ENTITY_TO_ROLE,
    DCAT,
    DCATAP,
    DCT,
    EUFORMAT,
    EUFREQ,
    FREQ,
    GEODCAT,
    HVD_LEGISLATION,
    IANAFORMAT,
    SCHEMA,
    SCV,
    SKOS,
    SPDX,
    TAG_TO_EU_HVD_CATEGORIES,
    contact_points_from_rdf,
    contact_points_to_rdf,
    namespace_manager,
    rdf_unique_values,
    rdf_value,
    remote_url_from_rdf,
    sanitize_html,
    schema_from_rdf,
    themes_from_rdf,
    url_from_rdf,
)
from udata.uris import endpoint_for
from udata.utils import get_by, safe_unicode, to_naive_datetime

from .constants import OGC_SERVICE_FORMATS, UPDATE_FREQUENCIES
from .models import Checksum, Dataset, License, Resource

log = logging.getLogger(__name__)

# Map extra frequencies (ie. not defined in Dublin Core) to closest equivalent
RDF_FREQUENCIES = {
    "punctual": None,
    "hourly": FREQ.continuous,
    "fourTimesADay": FREQ.daily,
    "threeTimesADay": FREQ.daily,
    "semidaily": FREQ.daily,
    "fourTimesAWeek": FREQ.threeTimesAWeek,
    "quinquennial": None,
    "unknown": None,
}

# Map european frequencies to their closest equivalent
# See:
#  - http://publications.europa.eu/mdr/resource/authority/frequency/html/frequencies-eng.html # noqa: E501
#  - https://publications.europa.eu/en/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency # noqa: E501
EU_RDF_REQUENCIES = {
    # Match Dublin Core name
    EUFREQ.ANNUAL: "annual",
    EUFREQ.BIENNIAL: "biennial",
    EUFREQ.TRIENNIAL: "triennial",
    EUFREQ.QUARTERLY: "quarterly",
    EUFREQ.MONTHLY: "monthly",
    EUFREQ.BIMONTHLY: "bimonthly",
    EUFREQ.WEEKLY: "weekly",
    EUFREQ.BIWEEKLY: "biweekly",
    EUFREQ.DAILY: "daily",
    # Name differs from Dublin Core
    EUFREQ.ANNUAL_2: "semiannual",
    EUFREQ.ANNUAL_3: "threeTimesAYear",
    EUFREQ.MONTHLY_2: "semimonthly",
    EUFREQ.MONTHLY_3: "threeTimesAMonth",
    EUFREQ.WEEKLY_2: "semiweekly",
    EUFREQ.WEEKLY_3: "threeTimesAWeek",
    EUFREQ.DAILY_2: "semidaily",
    EUFREQ.CONT: "continuous",
    EUFREQ.UPDATE_CONT: "continuous",
    EUFREQ.IRREG: "irregular",
    EUFREQ.UNKNOWN: "unknown",
    EUFREQ.OTHER: "unknown",
    EUFREQ.NEVER: "punctual",
}


def temporal_to_rdf(
    daterange: db.DateRange, graph: Optional[Graph] = None
) -> Optional[RdfResource]:
    if not daterange:
        return
    graph = graph or Graph(namespace_manager=namespace_manager)
    pot = graph.resource(BNode())
    pot.set(RDF.type, DCT.PeriodOfTime)
    pot.set(DCAT.startDate, Literal(daterange.start))
    if daterange.end:
        pot.set(DCAT.endDate, Literal(daterange.end))
    return pot


def frequency_to_rdf(frequency: str, graph: Optional[Graph] = None) -> Optional[str]:
    if not frequency:
        return
    return RDF_FREQUENCIES.get(frequency, getattr(FREQ, frequency))


def owner_to_rdf(dataset: Dataset, graph: Optional[Graph] = None) -> Optional[RdfResource]:
    from udata.core.organization.rdf import organization_to_rdf
    from udata.core.user.rdf import user_to_rdf

    if dataset.owner:
        return user_to_rdf(dataset.owner, graph)
    elif dataset.organization:
        return organization_to_rdf(dataset.organization, graph)
    return


def detect_ogc_service(resource: Resource) -> Optional[str]:
    """
    Detect if the resource points towards an OGC Service based on either
    * a known OGC Service format
    * a REQUEST=GetCapabilities param in url
    It returns the OGC service type or None
    """
    if resource.format and resource.format.strip("ogc:") in OGC_SERVICE_FORMATS:
        return resource.format.strip("ogc:")
    url = resource.url.lower()
    if "request=getcapabilities" in url and any(
        f"service={format}" in url for format in OGC_SERVICE_FORMATS
    ):
        return next(format for format in OGC_SERVICE_FORMATS if f"service={format}" in url)


def ogc_service_to_rdf(
    dataset: Dataset,
    resource: Resource,
    ogc_service_type: Optional[str] = None,
    graph: Optional[Graph] = None,
    is_hvd: bool = False,
) -> RdfResource:
    """
    Build a dataservice on the fly for OGC services distributions
    Inspired from https://github.com/SEMICeu/iso-19139-to-dcat-ap/blob/f61b2921dd398b90b2dd2db14085e75687f7616b/iso-19139-to-dcat-ap.xsl#L1419
    """
    graph = graph or Graph(namespace_manager=namespace_manager)
    service = graph.resource(BNode())
    service.set(RDF.type, DCAT.DataService)
    service.set(DCT.title, Literal(resource.title))
    service.set(DCAT.endpointURL, URIRef(resource.url.split("?")[0]))
    if "request=getcapabilities" in resource.url.lower():
        service.set(DCAT.endpointDescription, URIRef(resource.url))
    if ogc_service_type:
        service.set(
            DCT.conformsTo,
            URIRef("http://www.opengeospatial.org/standards/" + ogc_service_type),
        )

    if dataset and dataset.license:
        service.add(DCT.rights, Literal(dataset.license.title))
        if dataset.license.url:
            service.add(DCT.license, URIRef(dataset.license.url))

    if dataset and dataset.contact_points:
        for contact_point, predicate in contact_points_to_rdf(dataset.contact_points, graph):
            service.set(predicate, contact_point)

    if is_hvd:
        # DCAT-AP HVD applicable legislation is also expected at the distribution > accessService level
        service.add(DCATAP.applicableLegislation, URIRef(HVD_LEGISLATION))
        for tag in dataset.tags:
            # Add HVD category if this dataset is tagged HVD
            if tag in TAG_TO_EU_HVD_CATEGORIES:
                service.add(DCATAP.hvdCategory, URIRef(TAG_TO_EU_HVD_CATEGORIES[tag]))

    return service


def resource_to_rdf(
    resource: Resource,
    dataset: Optional[Dataset] = None,
    graph: Optional[Graph] = None,
    is_hvd: bool = False,
) -> RdfResource:
    """
    Map a Resource domain model to a DCAT/RDF graph
    """
    graph = graph or Graph(namespace_manager=namespace_manager)
    if dataset and dataset.id:
        id = URIRef(
            endpoint_for(
                "datasets.show_redirect",
                "api.dataset",
                dataset=dataset.id,
                _external=True,
                _anchor="resource-{0}".format(resource.id),
            )
        )
    else:
        id = BNode(resource.id)
    permalink = endpoint_for(
        "datasets.resource", "api.resource_redirect", id=resource.id, _external=True
    )
    r = graph.resource(id)
    r.set(RDF.type, DCAT.Distribution)
    r.set(DCT.identifier, Literal(resource.id))
    r.add(DCT.title, Literal(resource.title))
    r.add(DCT.description, Literal(resource.description))
    r.add(DCAT.downloadURL, URIRef(resource.url))
    r.add(DCAT.accessURL, URIRef(permalink))
    r.add(DCT.issued, Literal(resource.created_at))
    r.add(DCT.modified, Literal(resource.last_modified))
    if dataset and dataset.license:
        r.add(DCT.rights, Literal(dataset.license.title))
        if dataset.license.url:
            r.add(DCT.license, URIRef(dataset.license.url))
    if resource.filesize is not None:
        r.add(DCAT.byteSize, Literal(resource.filesize))
    if resource.mime:
        r.add(DCAT.mediaType, Literal(resource.mime))
    if resource.format:
        r.add(DCT.format, Literal(resource.format))
    if resource.checksum:
        checksum = graph.resource(BNode())
        checksum.set(RDF.type, SPDX.Checksum)
        algorithm = "checksumAlgorithm_{0}".format(resource.checksum.type)
        checksum.add(SPDX.algorithm, getattr(SPDX, algorithm))
        checksum.add(SPDX.checksumValue, Literal(resource.checksum.value))
        r.add(SPDX.checksum, checksum)
    if is_hvd:
        # DCAT-AP HVD applicable legislation is also expected at the distribution level
        r.add(DCATAP.applicableLegislation, URIRef(HVD_LEGISLATION))

    # Add access service for known OGC resources
    if ogc_service_type := detect_ogc_service(resource):
        r.add(
            DCAT.accessService,
            ogc_service_to_rdf(dataset, resource, ogc_service_type, graph, is_hvd),
        )

    return r


def dataset_to_graph_id(dataset: Dataset) -> URIRef | BNode:
    if dataset.harvest and dataset.harvest.uri:
        return URIRef(dataset.harvest.uri)
    elif dataset.id:
        return URIRef(
            endpoint_for(
                "datasets.show_redirect", "api.dataset", dataset=dataset.id, _external=True
            )
        )
    else:
        # Should not happen in production. Some test only
        # `build()` a dataset without saving it to the DB.
        return BNode()


def dataset_to_rdf(dataset: Dataset, graph: Optional[Graph] = None) -> RdfResource:
    """
    Map a dataset domain model to a DCAT/RDF graph
    """
    # Use the unlocalized permalink to the dataset as URI when available
    # unless there is already an upstream URI
    id = dataset_to_graph_id(dataset)

    graph = graph or Graph(namespace_manager=namespace_manager)
    d = graph.resource(id)

    # Expose upstream identifier if present
    if dataset.harvest and dataset.harvest.dct_identifier:
        d.set(DCT.identifier, Literal(dataset.harvest.dct_identifier))

        alt = graph.resource(BNode())
        alternate_identifier = Literal(
            endpoint_for(
                "datasets.show_redirect",
                "api.dataset",
                dataset=dataset.id,
                _external=True,
            )
        )
        alt.set(RDF.type, ADMS.Identifier)
        alt.set(DCT.creator, Literal(current_app.config["SITE_TITLE"]))
        alt.set(SKOS.notation, alternate_identifier)
        d.set(ADMS.identifier, alt)
    else:
        d.set(DCT.identifier, Literal(dataset.id))

    d.set(RDF.type, DCAT.Dataset)
    d.set(DCT.title, Literal(dataset.title))
    d.set(DCT.description, Literal(dataset.description))
    d.set(DCT.issued, Literal(dataset.created_at))
    d.set(DCT.modified, Literal(dataset.last_modified))

    if dataset.harvest and dataset.harvest.remote_url:
        d.set(DCAT.landingPage, URIRef(dataset.harvest.remote_url))
    elif dataset.id:
        d.set(
            DCAT.landingPage,
            URIRef(
                endpoint_for(
                    "datasets.show_redirect",
                    "api.dataset",
                    dataset=dataset.id,
                    _external=True,
                )
            ),
        )

    if dataset.acronym:
        d.set(SKOS.altLabel, Literal(dataset.acronym))

    # Add DCAT-AP HVD properties if the dataset is tagged hvd.
    # See https://semiceu.github.io/DCAT-AP/releases/2.2.0-hvd/
    is_hvd = current_app.config["HVD_SUPPORT"] and "hvd" in dataset.tags
    if is_hvd:
        d.add(DCATAP.applicableLegislation, URIRef(HVD_LEGISLATION))

    for tag in dataset.tags:
        d.add(DCAT.keyword, Literal(tag))
        # Add HVD category if this dataset is tagged HVD
        if is_hvd and tag in TAG_TO_EU_HVD_CATEGORIES:
            d.add(DCATAP.hvdCategory, URIRef(TAG_TO_EU_HVD_CATEGORIES[tag]))

    for resource in dataset.resources:
        d.add(DCAT.distribution, resource_to_rdf(resource, dataset, graph, is_hvd))

    if is_hvd:
        from udata.core.dataservices.models import Dataservice
        from udata.core.dataservices.rdf import dataservice_as_distribution_to_rdf

        # Add a blank distribution pointing to a DataService using the distribution DCAT.accessService.
        # Useful for HVD reporting since DataService are not currently harvested by
        # data.europa.eu as first class entities.
        # Should be removed once supported by data.europa.eu harvesting.
        for service in Dataservice.objects.filter(datasets=dataset, tags="hvd"):
            d.add(
                DCAT.distribution,
                dataservice_as_distribution_to_rdf(service, graph),
            )

    if dataset.temporal_coverage:
        d.set(DCT.temporal, temporal_to_rdf(dataset.temporal_coverage, graph))

    frequency = frequency_to_rdf(dataset.frequency)
    if frequency:
        d.set(DCT.accrualPeriodicity, frequency)

    owner_role = DCT.publisher
    if any(contact_point.role == "publisher" for contact_point in dataset.contact_points):
        # There's already a publisher, so the owner should instead be a distributor.
        owner_role = GEODCAT.distributor
    owner = owner_to_rdf(dataset, graph)
    if owner:
        d.set(owner_role, owner)

    for contact_point, predicate in contact_points_to_rdf(dataset.contact_points, graph):
        d.set(predicate, contact_point)

    return d


CHECKSUM_ALGORITHMS = {
    SPDX.checksumAlgorithm_md5: "md5",
    SPDX.checksumAlgorithm_sha1: "sha1",
    SPDX.checksumAlgorithm_sha256: "sha256",
}


def temporal_from_literal(text):
    """
    Parse a temporal coverage from a literal ie. either:
    - an ISO date range
    - a single ISO date period (month,year)
    """
    if text.count("/") == 1:
        # This is an ISO date range as preconized by Gov.uk
        # http://guidance.data.gov.uk/dcat_fields.html
        start, end = text.split("/")
        return db.DateRange(start=parse_dt(start).date(), end=parse_dt(end).date())
    else:
        separators = text.count("-")
        if separators == 0:
            # this is a year
            return db.DateRange(start=date(int(text), 1, 1), end=date(int(text), 12, 31))
        elif separators == 1:
            # this is a month
            dt = parse_dt(text).date()
            return db.DateRange(
                start=dt.replace(day=1),
                end=dt.replace(day=calendar.monthrange(dt.year, dt.month)[1]),
            )


def temporal_from_resource(resource):
    """
    Parse a temporal coverage from a RDF class/resource ie. either:
    - a `dct:PeriodOfTime` with schema.org `startDate` and `endDate` properties
    - a `dct:PeriodOfTime` with DCAT `startDate` and `endDate` properties
    - an inline gov.uk Time Interval value
    - an URI reference to a gov.uk Time Interval ontology
      http://reference.data.gov.uk/
    """
    if isinstance(resource.identifier, URIRef):
        # Fetch remote ontology if necessary
        g = Graph().parse(str(resource.identifier))
        resource = g.resource(resource.identifier)
    if resource.value(SCHEMA.startDate):
        end = resource.value(SCHEMA.endDate)
        return db.DateRange(
            start=resource.value(SCHEMA.startDate).toPython(),
            end=end.toPython() if end else None,
        )
    elif resource.value(DCAT.startDate):
        end = resource.value(DCAT.endDate)
        return db.DateRange(
            start=resource.value(DCAT.startDate).toPython(),
            end=end.toPython() if end else None,
        )
    elif resource.value(SCV.min):
        end = resource.value(SCV.max)
        return db.DateRange(
            start=resource.value(SCV.min).toPython(),
            end=end.toPython() if end else None,
        )


def temporal_from_rdf(period_of_time):
    """Failsafe parsing of a temporal coverage"""
    try:
        if isinstance(period_of_time, Literal):
            return temporal_from_literal(str(period_of_time))
        elif isinstance(period_of_time, RdfResource):
            return temporal_from_resource(period_of_time)
    except Exception:
        # There are a lot of cases where parsing could/should fail
        # but we never want to break the whole dataset parsing
        # so we log the error for future investigation and improvement
        log.warning("Unable to parse temporal coverage", exc_info=True)


def spatial_from_rdf(graph):
    geojsons = []
    for term in graph.objects(DCT.spatial):
        try:
            # This may not be official in the norm but some ArcGis return
            # bbox as literal directly in DCT.spatial.
            if isinstance(term, Literal):
                geojson = bbox_to_geojson_multipolygon(term.toPython())
                if geojson is not None:
                    geojsons.append(geojson)

                continue

            for object in term.objects():
                if isinstance(object, Literal):
                    if (
                        object.datatype.__str__()
                        == "https://www.iana.org/assignments/media-types/application/vnd.geo+json"
                    ):
                        try:
                            geojson = json.loads(object.toPython())
                        except ValueError as e:
                            log.warning(f"Invalid JSON in spatial GeoJSON {object.toPython()} {e}")
                            continue
                    elif object.datatype.__str__() == "http://www.opengis.net/rdf#wktLiteral":
                        try:
                            # .upper() si here because geomet doesn't support Polygon but only POLYGON
                            geojson = wkt.loads(object.toPython().strip().upper())
                        except ValueError as e:
                            log.warning(f"Invalid JSON in spatial WKT {object.toPython()} {e}")
                            continue
                    else:
                        continue

                    geojsons.append(geojson)
        except Exception as e:
            log.exception(
                f"Exception during `spatial_from_rdf` for term {term}: {e}", stack_info=True
            )

    if not geojsons:
        return None

    # We first try to build a big MultiPolygon with all the spatial coverages found in RDF.
    # We deduplicate the coordinates because some backend provides the same coordinates multiple
    # times in different format. We only support in this first pass Polygons and MultiPolygons. Not sure
    # if there are other types of spatial coverage worth integrating (points? line strings?). But these other
    # formats are not compatible to be merged in the unique stored representation in MongoDB, we'll deal with them in a second pass.
    # The merging lose the properties and other information inside the GeoJSON…
    # Note that having multiple `Polygon` is not really the DCAT way of doing things, the standard require that you use
    # a `MultiPolygon` in this case. We support this right now, and wait and see if it raises problems in the future for
    # people following the standard. (see https://github.com/datagouv/data.gouv.fr/issues/1362#issuecomment-2112774115)
    polygons = []
    for geojson in geojsons:
        if geojson["type"] == "Polygon":
            if geojson["coordinates"] not in polygons:
                polygons.append(geojson["coordinates"])
        elif geojson["type"] == "MultiPolygon":
            for coordinates in geojson["coordinates"]:
                if coordinates not in polygons:
                    polygons.append(coordinates)
        else:
            log.warning(f"Unsupported GeoJSON type '{geojson['type']}'")
            continue

    if not polygons:
        log.warning("No supported types found in the GeoJSON data.")
        return None

    spatial_coverage = SpatialCoverage(
        geom={
            "type": "MultiPolygon",
            "coordinates": polygons,
        }
    )

    try:
        spatial_coverage.clean()
        return spatial_coverage
    except ValidationError as e:
        log.warning(f"Cannot save the spatial coverage {coordinates} (error was {e})")
        return None


def frequency_from_rdf(term):
    if isinstance(term, str):
        try:
            term = URIRef(uris.validate(term))
        except uris.ValidationError:
            pass
    if isinstance(term, Literal):
        if term.toPython().lower() in UPDATE_FREQUENCIES:
            return term.toPython().lower()
    if isinstance(term, RdfResource):
        term = term.identifier
    if isinstance(term, URIRef):
        if EUFREQ in term:
            return EU_RDF_REQUENCIES.get(term)
        _, _, freq = namespace_manager.compute_qname(term)
        if freq.lower() in UPDATE_FREQUENCIES:
            return freq.lower()


def mime_from_rdf(resource):
    # DCAT.mediaType *should* only be used when defined as IANA
    mime = rdf_value(resource, DCAT.mediaType)
    if not mime:
        return
    if IANAFORMAT in mime:
        return "/".join(mime.split("/")[-2:])
    if isinstance(mime, str):
        return mime


def format_from_rdf(resource):
    format = rdf_value(resource, DCT.format)
    if not format:
        return
    if EUFORMAT in format or IANAFORMAT in format:
        _, _, format = namespace_manager.compute_qname(URIRef(format))
        return format.lower()
    return format.lower()


def title_from_rdf(rdf, url):
    """
    Try to extract a distribution title from a property.
    As it's not a mandatory property,
    it fallback on building a title from the URL
    then the format and in last ressort a generic resource name.
    """
    title = rdf_value(rdf, DCT.title)
    if title:
        return title
    if url:
        last_part = url.split("/")[-1]
        if "." in last_part and "?" not in last_part:
            return last_part
    fmt = rdf_value(rdf, DCT.format)
    lang = current_app.config["DEFAULT_LANGUAGE"]
    with i18n.language(lang):
        if fmt:
            return i18n._("{format} resource").format(format=fmt.lower())
        else:
            return i18n._("Nameless resource")


def access_rights_from_rdf(resource: RdfResource) -> set[str]:
    """
    Extract the access rights from a RdfResource
    Cardinality is 0..n (although it should be 0..1 per the spec).
    """
    return rdf_unique_values(resource, DCT.accessRights, parse_label=True)


def licenses_from_rdf(resource: RdfResource) -> set[str]:
    """
    Extract licences from a RDF distribution.
    See `test_dataset_rdf.py > test_licenses_from_rdf` for examples of supported formats.
    Cardinality is 0..n (although it should be 0..1 per the spec).
    """
    return rdf_unique_values(resource, DCT.license, parse_label=True)


def rights_from_rdf(resource: RdfResource) -> set[str]:
    """
    Extract rights from a RDF distribution.
    Cardinality is 0..n.
    """
    return rdf_unique_values(resource, DCT.rights, parse_label=True)


def provenances_from_rdf(resource: RdfResource) -> set[str]:
    """
    Extract provenance from a RDF distribution.
    Cardinality is 0..n.
    """
    return rdf_unique_values(resource, DCT.provenance, parse_label=True)


def infer_dataset_access_rights(
    dataset: RdfResource, resources_access_rights: list[set]
) -> set | None:
    """
    Infer the dataset access rights from a RDF dataset or a list of resources access rights.
    If the dataset does not have access rights and all resources have the same set of access rights return it.
    """
    dataset_access_rights = access_rights_from_rdf(dataset)
    if not dataset_access_rights and resources_access_rights:
        if set.union(*resources_access_rights) == set.intersection(*resources_access_rights):
            dataset_access_rights = resources_access_rights[0]
    return dataset_access_rights


def add_dcat_extra(
    obj: Dataset | Resource, key: str, value: str | set | list
) -> Dataset | Resource:
    if type(value) is set:
        value = list(value)
    obj.extras["dcat"] = {
        **obj.extras.get("dcat", {}),
        key: value,
    }
    return obj


def resource_from_rdf(graph_or_distrib, dataset=None, is_additionnal=False):
    """
    Map a Resource domain model to a DCAT/RDF graph
    """
    if isinstance(graph_or_distrib, RdfResource):
        distrib = graph_or_distrib
    else:
        node = graph_or_distrib.value(predicate=RDF.type, object=DCAT.Distribution)
        distrib = graph_or_distrib.resource(node)

    if not is_additionnal:
        download_url = url_from_rdf(distrib, DCAT.downloadURL)
        access_url = url_from_rdf(distrib, DCAT.accessURL)
        url = safe_unicode(download_url or access_url)
    else:
        url = distrib.identifier.toPython() if isinstance(distrib.identifier, URIRef) else None
    # we shouldn't create resources without URLs
    if not url:
        log.warning(f"Resource without url: {distrib}")
        return

    if dataset:
        resource = get_by(dataset.resources, "url", url)
    if not dataset or not resource:
        resource = Resource()
        if dataset:
            dataset.resources.append(resource)
    resource.filetype = "remote"
    resource.title = title_from_rdf(distrib, url)
    resource.url = url
    resource.description = sanitize_html(distrib.value(DCT.description))
    resource.filesize = rdf_value(distrib, DCAT.byteSize)
    resource.mime = mime_from_rdf(distrib)
    resource.format = format_from_rdf(distrib)
    schema = schema_from_rdf(distrib)
    if schema:
        resource.schema = schema

    access_rights = access_rights_from_rdf(distrib)
    if access_rights:
        add_dcat_extra(resource, "accessRights", access_rights)

    licenses = licenses_from_rdf(distrib)
    if licenses:
        add_dcat_extra(resource, "license", licenses)

    rights = rights_from_rdf(distrib)
    if rights:
        add_dcat_extra(resource, "rights", rights)

    checksum = distrib.value(SPDX.checksum)
    if checksum:
        algorithm = checksum.value(SPDX.algorithm).identifier
        algorithm = CHECKSUM_ALGORITHMS.get(algorithm)
        if algorithm:
            resource.checksum = Checksum()
            resource.checksum.value = rdf_value(checksum, SPDX.checksumValue)
            resource.checksum.type = algorithm
    if is_additionnal:
        resource.type = "other"
    elif distrib.value(DCAT.accessService):
        # The distribution has a DCAT.accessService property, we deduce
        # that the distribution is of type API
        resource.type = "api"

    identifier = rdf_value(distrib, DCT.identifier)
    uri = distrib.identifier.toPython() if isinstance(distrib.identifier, URIRef) else None
    created_at = rdf_value(distrib, DCT.issued)
    modified_at = rdf_value(distrib, DCT.modified)

    if not resource.harvest:
        resource.harvest = HarvestResourceMetadata()
    resource.harvest.created_at = created_at

    # In the past, we've encountered future `modified_at` during harvesting
    # do not save it. :FutureHarvestModifiedAt
    if modified_at and to_naive_datetime(modified_at) > datetime.utcnow():
        log.warning(f"Future `DCT.modified` date '{modified_at}' in resource")
    else:
        resource.harvest.modified_at = modified_at

    resource.harvest.dct_identifier = identifier
    resource.harvest.uri = uri

    return resource


def dataset_from_rdf(graph: Graph, dataset=None, node=None, remote_url_prefix: str | None = None):
    """
    Create or update a dataset from a RDF/DCAT graph
    """
    dataset = dataset or Dataset()

    if node is None:  # Assume first match is the only match
        node = graph.value(predicate=RDF.type, object=DCAT.Dataset)

    d = graph.resource(node)

    dataset.title = rdf_value(d, DCT.title)
    if not dataset.title:
        # If the dataset is externaly defined (so without title and just with a link to the dataset XML)
        # we should have skipped it way before in :ExcludeExternalyDefinedDataset
        raise HarvestSkipException("missing title on dataset")

    # Support dct:abstract if dct:description is missing (sometimes used instead)
    description = d.value(DCT.description) or d.value(DCT.abstract)
    dataset.description = sanitize_html(description)
    dataset.frequency = frequency_from_rdf(d.value(DCT.accrualPeriodicity))
    roles = [  # Imbricated list of contact points for each role
        contact_points_from_rdf(d, rdf_entity, role, dataset)
        for rdf_entity, role in CONTACT_POINT_ENTITY_TO_ROLE.items()
    ]
    dataset.contact_points = [  # Flattened list of contact points
        contact_point for role in roles for contact_point in role
    ] or dataset.contact_points
    schema = schema_from_rdf(d)
    if schema:
        dataset.schema = schema

    spatial_coverage = spatial_from_rdf(d)
    if spatial_coverage:
        dataset.spatial = spatial_coverage

    acronym = rdf_value(d, SKOS.altLabel)
    if acronym:
        dataset.acronym = acronym

    dataset.tags = themes_from_rdf(d)

    temporal_coverage = temporal_from_rdf(d.value(DCT.temporal))
    if temporal_coverage:
        dataset.temporal_coverage = temporal_coverage

    provenances = provenances_from_rdf(d)
    if provenances:
        add_dcat_extra(dataset, "provenance", provenances)

    resources_licenses_hints = set()
    resources_access_rights = []
    for distrib in d.objects(DCAT.distribution | DCAT.distributions):
        resource_from_rdf(distrib, dataset)
        resources_access_rights.append(access_rights_from_rdf(distrib))
        # include both dct:license and dct:rights as licenses hints from resources
        resources_licenses_hints |= licenses_from_rdf(distrib)
        resources_licenses_hints |= rights_from_rdf(distrib)

    for additionnal in d.objects(DCT.hasPart):
        resource_from_rdf(additionnal, dataset, is_additionnal=True)

    dataset_access_rights = infer_dataset_access_rights(d, resources_access_rights)
    if dataset_access_rights:
        add_dcat_extra(dataset, "accessRights", dataset_access_rights)

    default_license = dataset.license or License.default()
    dataset_licenses = licenses_from_rdf(d)
    if dataset_licenses:
        add_dcat_extra(dataset, "license", dataset_licenses)
    dataset_rights = rights_from_rdf(d)
    if dataset_rights:
        add_dcat_extra(dataset, "rights", dataset_rights)
    dataset.license = License.guess(
        *dataset_licenses,
        *dataset_rights,
        *resources_licenses_hints,
        default=default_license,
    )

    identifier = rdf_value(d, DCT.identifier)
    uri = d.identifier.toPython() if isinstance(d.identifier, URIRef) else None

    remote_url = remote_url_from_rdf(d, graph, remote_url_prefix=remote_url_prefix)

    created_at = rdf_value(d, DCT.issued)
    modified_at = rdf_value(d, DCT.modified)

    if not dataset.harvest:
        dataset.harvest = HarvestDatasetMetadata()
    dataset.harvest.dct_identifier = identifier
    dataset.harvest.uri = uri
    dataset.harvest.remote_url = remote_url
    dataset.harvest.created_at = created_at

    # In the past, we've encountered future `modified_at` during harvesting
    # do not save it. :FutureHarvestModifiedAt
    if modified_at and to_naive_datetime(modified_at) > datetime.utcnow():
        log.warning(f"Future `DCT.modified` date '{modified_at}' in dataset")
    else:
        dataset.harvest.modified_at = modified_at

    return dataset


def bbox_to_geojson_multipolygon(bbox_as_str: str) -> dict | None:
    bbox = bbox_as_str.strip().split(",")
    if len(bbox) != 4:
        return None

    west = float(bbox[0])
    south = float(bbox[1])
    east = float(bbox[2])
    north = float(bbox[3])

    low_left = [west, south]
    top_left = [west, north]
    top_right = [east, north]
    low_right = [east, south]

    return {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [low_left, low_right, top_right, top_left, low_left],
            ],
        ],
    }
