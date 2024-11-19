"""
This module centralize udata-wide RDF helpers and configuration
"""

import logging
import re
from html.parser import HTMLParser

from flask import abort, current_app, request, url_for
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import (
    DCTERMS,
    FOAF,
    RDF,
    RDFS,
    SKOS,
    XSD,
    Namespace,
    NamespaceManager,
)
from rdflib.resource import Resource as RdfResource
from rdflib.util import SUFFIX_FORMAT_MAP
from rdflib.util import guess_format as raw_guess_format

from udata import uris
from udata.core.contact_point.models import ContactPoint
from udata.frontend.markdown import parse_html
from udata.models import Schema
from udata.mongo.errors import FieldValidationError
from udata.tags import slug as slugify_tag
from udata.uris import endpoint_for

log = logging.getLogger(__name__)

# Extra Namespaces
ADMS = Namespace("http://www.w3.org/ns/adms#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCATAP = Namespace("http://data.europa.eu/r5r/")
HYDRA = Namespace("http://www.w3.org/ns/hydra/core#")
SCHEMA = Namespace("http://schema.org/")
SCV = Namespace("http://purl.org/NET/scovo#")
SPDX = Namespace("http://spdx.org/rdf/terms#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
FREQ = Namespace("http://purl.org/cld/freq/")
EUFREQ = Namespace("http://publications.europa.eu/resource/authority/frequency/")  # noqa: E501
EUFORMAT = Namespace("http://publications.europa.eu/resource/authority/file-type/")
IANAFORMAT = Namespace("https://www.iana.org/assignments/media-types/")
DCT = DCTERMS  # More common usage
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")

namespace_manager = NamespaceManager(Graph())
namespace_manager.bind("adms", ADMS)
namespace_manager.bind("dcat", DCAT)
namespace_manager.bind("dcatap", DCATAP)
namespace_manager.bind("dct", DCT)
namespace_manager.bind("foaf", FOAF)
namespace_manager.bind("foaf", FOAF)
namespace_manager.bind("hydra", HYDRA)
namespace_manager.bind("rdfs", RDFS)
namespace_manager.bind("scv", SCV)
namespace_manager.bind("skos", SKOS)
namespace_manager.bind("vcard", VCARD)
namespace_manager.bind("xsd", XSD)
namespace_manager.bind("freq", FREQ)

# Support JSON-LD in format detection
FORMAT_MAP = SUFFIX_FORMAT_MAP.copy()
FORMAT_MAP["json"] = "json-ld"
FORMAT_MAP["jsonld"] = "json-ld"
FORMAT_MAP["xml"] = "xml"

# Map serialization formats to MIME types
RDF_MIME_TYPES = {
    "xml": "application/rdf+xml",
    "n3": "text/n3",
    "turtle": "application/x-turtle",
    "nt": "application/n-triples",
    "json-ld": "application/ld+json",
    "trig": "application/trig",
    # Available but not activated
    # 'nquads': 'application/n-quads',
    # 'trix': 'text/xml',
}

# Map accepted MIME types to known formats
ACCEPTED_MIME_TYPES = {
    "application/rdf+xml": "xml",
    "application/xml": "xml",
    "text/n3": "n3",
    "application/x-turtle": "turtle",
    "text/turtle": "turtle",
    "application/n-triples": "nt",
    "application/ld+json": "json-ld",
    "application/json": "json-ld",
    "application/trig": "trig",
    "text/xml": "xml",
    # Available but not activated
    # 'application/n-quads': 'nquads',
    # 'text/xml': 'trix',
}

# Map formats to default used extensions
RDF_EXTENSIONS = {
    "xml": "xml",
    "n3": "n3",
    "turtle": "ttl",
    "nt": "nt",
    "trig": "trig",
    "json-ld": "json",
    # Available but not activated
    # 'nquads': 'nq',
    # 'trix': 'trix',
}

# Includes control characters, unicode surrogate characters and unicode end-of-plane non-characters
ILLEGAL_XML_CHARS = "[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]"

# Map High Value Datasets URIs to keyword categories
EU_HVD_CATEGORIES = {
    "http://data.europa.eu/bna/c_164e0bf5": "Météorologiques",
    "http://data.europa.eu/bna/c_a9135398": "Entreprises et propriété d'entreprises",
    "http://data.europa.eu/bna/c_ac64a52d": "Géospatiales",
    "http://data.europa.eu/bna/c_b79e35eb": "Mobilité",
    "http://data.europa.eu/bna/c_dd313021": "Observation de la terre et environnement",
    "http://data.europa.eu/bna/c_e1da4e07": "Statistiques",
}
HVD_LEGISLATION = "http://data.europa.eu/eli/reg_impl/2023/138/oj"
TAG_TO_EU_HVD_CATEGORIES = {slugify_tag(EU_HVD_CATEGORIES[uri]): uri for uri in EU_HVD_CATEGORIES}


def guess_format(string):
    """Guess format given an extension or a mime-type"""
    if string in ACCEPTED_MIME_TYPES:
        return ACCEPTED_MIME_TYPES[string]
    return raw_guess_format(string, FORMAT_MAP)


def negociate_content(default="json-ld"):
    """Perform a content negociation on the format given the Accept header"""
    mimetype = request.accept_mimetypes.best_match(ACCEPTED_MIME_TYPES.keys())
    return ACCEPTED_MIME_TYPES.get(mimetype, default)


def want_rdf():
    """Check wether client prefer RDF over the default HTML"""
    mimetype = request.accept_mimetypes.best
    return mimetype in ACCEPTED_MIME_TYPES


# JSON-LD context used for udata DCAT representation
CONTEXT = {
    # Namespaces
    "@vocab": "http://www.w3.org/ns/dcat#",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "org": "http://www.w3.org/ns/org#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "spdx": "http://spdx.org/rdf/terms#",
    "vcard": "http://www.w3.org/2006/vcard/ns#",
    "schema": "http://schema.org/",
    "hydra": "http://www.w3.org/ns/hydra/core#",
    "freq": "http://purl.org/cld/freq/",
    # Aliased field
    "downloadURL": {"@id": "dcat:downloadURL", "@type": "@id"},
    "accessURL": {"@id": "dcat:accessURL", "@type": "@id"},
    "dataset": {"@id": "dcat:dataset", "@type": "@id"},
    "distribution": {"@id": "dcat:distribution", "@type": "@id"},
    "title": "dct:title",
    "description": "dct:description",
    "issued": {"@id": "dct:issued", "@type": "http://www.w3.org/2001/XMLSchema#dateTime"},
    "modified": {"@id": "dct:modified", "@type": "http://www.w3.org/2001/XMLSchema#dateTime"},
    "language": "dct:language",
    "license": "dct:license",
    "rights": "dct:rights",
    "spatial": "dct:spatial",
    "identifier": "dct:identifier",
    "temporal": "dct:temporal",
    "format": "dct:format",
    "accrualPeriodicity": "dct:accrualPeriodicity",
    "homepage": {"@id": "foaf:homepage", "@type": "@id"},
    "publisher": {"@id": "dct:publisher", "@type": "@id"},
    "fn": "vcard:fn",
    "hasEmail": "vcard:email",
    "subOrganizationOf": "org:subOrganizationOf",
    "checksum": "spdx:checksum",
    "algorithm": {"@id": "spdx:algorithm", "@type": "@id"},
    "checksumValue": "spdx:checksumValue",
    "label": "rdfs:label",
    "name": "foaf:name",
    "startDate": "schema:startDate",
    "endDate": "schema:endDate",
    "view": {"@id": "hydra:view", "@type": "@id"},
    "first": {"@id": "hydra:first", "@type": "@id"},
    "last": {"@id": "hydra:last", "@type": "@id"},
    "next": {"@id": "hydra:next", "@type": "@id"},
    "previous": {"@id": "hydra:previous", "@type": "@id"},
    "totalItems": "hydra:totalItems",
}


def serialize_value(value, parse_label=False):
    """
    If the value is a URIRef or a Literal, return it as a string.
    If the value is a RdfResource:
        - Return the label of the RdfResource if any and `parse_label`,
        - or the identifier of the RdfResource.
    """
    if isinstance(value, (URIRef, Literal)):
        return value.toPython()
    elif isinstance(value, RdfResource):
        if parse_label and (rdfs_label := rdf_value(value, RDFS.label)):
            return rdfs_label
        return value.identifier.toPython()


def rdf_unique_values(resource, predicate, parse_label=False) -> set[str]:
    """Returns a set of serialized values for a predicate from a RdfResource"""
    return {
        value
        for info in resource.objects(predicate=predicate)
        if (value := serialize_value(info, parse_label=parse_label))
    }


def rdf_value(obj, predicate, default=None, parse_label=False):
    """Serialize the value for a predicate on a RdfResource"""
    value = obj.value(predicate)
    return serialize_value(value, parse_label=parse_label) if value else default


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


def sanitize_html(text):
    text = text.toPython() if isinstance(text, Literal) else ""
    if is_html(text):
        return parse_html(text)
    else:
        return text.strip()


def url_from_rdf(rdf, prop):
    """
    Try to extract An URL from a resource property.
    It can be expressed in many forms as a URIRef or a Literal
    """
    value = rdf.value(prop)
    if isinstance(value, (URIRef, Literal)):
        return value.toPython()
    elif isinstance(value, RdfResource):
        return value.identifier.toPython()


def theme_labels_from_rdf(rdf):
    """
    Get theme labels to use as keywords.
    Map HVD keywords from known URIs resources if HVD support is activated.
    """
    for theme in rdf.objects(DCAT.theme):
        if isinstance(theme, RdfResource):
            uri = theme.identifier.toPython()
            if current_app.config["HVD_SUPPORT"] and uri in EU_HVD_CATEGORIES:
                label = EU_HVD_CATEGORIES[uri]
                # Additionnally yield hvd keyword
                yield "hvd"
            else:
                label = rdf_value(theme, SKOS.prefLabel)
        else:
            label = theme.toPython()
        if label:
            yield label


def themes_from_rdf(rdf):
    tags = [tag.toPython() for tag in rdf.objects(DCAT.keyword)]
    tags += theme_labels_from_rdf(rdf)
    return list(set(tags))


def contact_point_from_rdf(rdf, dataset):
    contact_point = rdf.value(DCAT.contactPoint)
    if contact_point:
        name = rdf_value(contact_point, VCARD.fn) or ""
        email = (
            rdf_value(contact_point, VCARD.hasEmail)
            or rdf_value(contact_point, VCARD.email)
            or rdf_value(contact_point, DCAT.email)
        )
        email = email.replace("mailto:", "").strip() if email else None
        contact_form = rdf_value(contact_point, VCARD.hasUrl)
        if not email and not contact_form:
            return
        if dataset.organization:
            contact, _ = ContactPoint.objects.get_or_create(
                name=name, email=email, contact_form=contact_form, organization=dataset.organization
            )
        elif dataset.owner:
            contact, _ = ContactPoint.objects.get_or_create(
                name=name, email=email, contact_form=contact_form, owner=dataset.owner
            )
        else:
            contact = None
        return contact


def contact_point_to_rdf(contact, graph=None):
    """
    Map a contact point to a DCAT/RDF graph
    """
    if not contact:
        return None

    graph = graph or Graph(namespace_manager=namespace_manager)

    if contact.id:
        id = URIRef(
            endpoint_for(
                "api.contact_point",
                contact_point=contact.id,
                _external=True,
            )
        )
    else:
        id = BNode()

    node = graph.resource(id)
    node.set(RDF.type, VCARD.Kind)
    if contact.name:
        node.set(VCARD.fn, Literal(contact.name))
    if contact.email:
        node.set(VCARD.hasEmail, URIRef(f"mailto:{contact.email}"))
    if contact.contact_form:
        node.set(VCARD.hasUrl, URIRef(contact.contact_form))
    return node


def primary_topic_identifier_from_rdf(graph: Graph, resource: RdfResource):
    """
    Extract the dct:identifier from a primaryTopic of a RdfResource `resource` via an RDF `graph`.
    The primary topic might be identified by a FOAF:isPrimaryTopicOf from the Resource, or by a FOAF:primaryTopic to the Resource.
    In DCAT, the primary topic should be a unique CatalogRecord (if any), but nothing here prevents it to be something else.
    """
    # look for "inner" primaryTopic linking to Dataset via isPrimaryTopicOf
    is_primary_topic_of = graph.value(subject=resource.identifier, predicate=FOAF.isPrimaryTopicOf)
    if is_primary_topic_of:
        return graph.value(is_primary_topic_of, DCT.identifier)
    # look for "outer" primaryTopic linking to Dataset via primaryTopic
    primary_topic = graph.value(predicate=FOAF.primaryTopic, object=resource.identifier)
    if primary_topic:
        return graph.value(primary_topic, DCT.identifier)


def remote_url_from_rdf(rdf: RdfResource, graph: Graph, remote_url_prefix: str | None = None):
    """
    Compute from `remote_url_prefix` if provided and primaryTopic identifier if found.
    Otherwise, use DCAT.landingPage if found and uri validation succeeds.
    In this latter case, use RDF identifier as fallback if uri validation succeeds.
    """
    if remote_url_prefix and (
        primary_topic_identifier := primary_topic_identifier_from_rdf(graph, rdf)
    ):
        return f"{remote_url_prefix.rstrip('/')}/{primary_topic_identifier}"

    landing_page = url_from_rdf(rdf, DCAT.landingPage)
    uri = rdf.identifier.toPython()
    for candidate in [landing_page, uri]:
        if candidate:
            try:
                uris.validate(candidate)
                return candidate
            except uris.ValidationError:
                pass


def schema_from_rdf(rdf):
    """
    Try to extract a schema from a conformsTo property.
    Currently the "issued" property is not harvest.
    """
    resource = rdf.value(DCT.conformsTo)
    if not resource:
        return None

    schema = Schema()
    if isinstance(resource, (URIRef, Literal)):
        schema.url = resource.toPython()
    elif isinstance(resource, RdfResource):
        # We try to get the schema "correct" URL.
        # 1. The identifier of the DCT.conformsTo
        # 2. The DCT.type inside the DCT.conformsTo (from some example it's the most precise one)
        # (other not currently used RDF.type)
        url = None
        try:
            url = uris.validate(resource.identifier.toPython())
        except uris.ValidationError:
            try:
                type = resource.value(DCT.type)
                if type is not None:
                    url = uris.validate(type.identifier.toPython())
            except uris.ValidationError:
                pass

        if url is None:
            return None

        schema.url = url
        schema.name = resource.value(DCT.title)
    else:
        return None

    try:
        schema.clean()
        return schema
    except FieldValidationError as e:
        log.warning(f"Invalid schema inside RDF {e}")
        return None


def escape_xml_illegal_chars(val, replacement="?"):
    illegal_xml_chars_RE = re.compile(ILLEGAL_XML_CHARS)
    return illegal_xml_chars_RE.sub(replacement, val)


def paginate_catalog(catalog, graph, datasets, format, rdf_catalog_endpoint, **values):
    if not format:
        raise ValueError("Pagination requires format")
    catalog.add(RDF.type, HYDRA.Collection)
    catalog.set(HYDRA.totalItems, Literal(datasets.total))
    kwargs = {
        "format": format,
        "page_size": datasets.page_size,
        "_external": True,
    }

    kwargs.update(values)

    first_url = url_for(rdf_catalog_endpoint, page=1, **kwargs)
    page_url = url_for(rdf_catalog_endpoint, page=datasets.page, **kwargs)
    last_url = url_for(rdf_catalog_endpoint, page=datasets.pages, **kwargs)
    pagination = graph.resource(URIRef(page_url))
    pagination.set(RDF.type, HYDRA.PartialCollectionView)

    pagination.set(HYDRA.first, URIRef(first_url))
    pagination.set(HYDRA.last, URIRef(last_url))
    if datasets.has_next:
        next_url = url_for(rdf_catalog_endpoint, page=datasets.page + 1, **kwargs)
        pagination.set(HYDRA.next, URIRef(next_url))
    if datasets.has_prev:
        prev_url = url_for(rdf_catalog_endpoint, page=datasets.page - 1, **kwargs)
        pagination.set(HYDRA.previous, URIRef(prev_url))

    catalog.set(HYDRA.view, pagination)

    return catalog


def graph_response(graph, format):
    """
    Return a proper flask response for a RDF resource given an expected format.
    """
    fmt = guess_format(format)
    if not fmt:
        abort(404)
    headers = {"Content-Type": RDF_MIME_TYPES[fmt]}
    kwargs = {}
    if fmt == "json-ld":
        kwargs["context"] = CONTEXT
    if isinstance(graph, RdfResource):
        graph = graph.graph
    return escape_xml_illegal_chars(graph.serialize(format=fmt, **kwargs)), 200, headers
