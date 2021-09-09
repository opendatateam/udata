'''
This module centralize udata-wide RDF helpers and configuration
'''
import re

from flask import request, url_for, abort

from rdflib import Graph, Literal, URIRef
from rdflib.resource import Resource as RdfResource
from rdflib.namespace import (
    Namespace, NamespaceManager, DCTERMS, SKOS, FOAF, XSD, RDFS, RDF
)
from rdflib.util import SUFFIX_FORMAT_MAP, guess_format as raw_guess_format

# Extra Namespaces
ADMS = Namespace('http://www.w3.org/ns/adms#')
DCAT = Namespace('http://www.w3.org/ns/dcat#')
HYDRA = Namespace('http://www.w3.org/ns/hydra/core#')
SCHEMA = Namespace('http://schema.org/')
SCV = Namespace('http://purl.org/NET/scovo#')
SPDX = Namespace('http://spdx.org/rdf/terms#')
VCARD = Namespace('http://www.w3.org/2006/vcard/ns#')
FREQ = Namespace('http://purl.org/cld/freq/')
EUFREQ = Namespace('http://publications.europa.eu/resource/authority/frequency/')  # noqa: E501
DCT = DCTERMS  # More common usage

namespace_manager = NamespaceManager(Graph())
namespace_manager.bind('dcat', DCAT)
namespace_manager.bind('dct', DCT)
namespace_manager.bind('foaf', FOAF)
namespace_manager.bind('foaf', FOAF)
namespace_manager.bind('hydra', HYDRA)
namespace_manager.bind('rdfs', RDFS)
namespace_manager.bind('scv', SCV)
namespace_manager.bind('skos', SKOS)
namespace_manager.bind('vcard', VCARD)
namespace_manager.bind('xsd', XSD)
namespace_manager.bind('freq', FREQ)

# Support JSON-LD in format detection
FORMAT_MAP = SUFFIX_FORMAT_MAP.copy()
FORMAT_MAP['json'] = 'json-ld'
FORMAT_MAP['jsonld'] = 'json-ld'
FORMAT_MAP['xml'] = 'xml'

# Map serialization formats to MIME types
RDF_MIME_TYPES = {
    'xml': 'application/rdf+xml',
    'n3': 'text/n3',
    'turtle': 'application/x-turtle',
    'nt': 'application/n-triples',
    'json-ld': 'application/ld+json',
    'trig': 'application/trig',
    # Available but not activated
    # 'nquads': 'application/n-quads',
    # 'trix': 'text/xml',
}

# Map accepted MIME types to known formats
ACCEPTED_MIME_TYPES = {
    'application/rdf+xml': 'xml',
    'application/xml': 'xml',
    'text/n3': 'n3',
    'application/x-turtle': 'turtle',
    'text/turtle': 'turtle',
    'application/n-triples': 'nt',
    'application/ld+json': 'json-ld',
    'application/json': 'json-ld',
    'application/trig': 'trig',
    # Available but not activated
    # 'application/n-quads': 'nquads',
    # 'text/xml': 'trix',
}

# Map formats to default used extensions
RDF_EXTENSIONS = {
    'xml': 'xml',
    'n3': 'n3',
    'turtle': 'ttl',
    'nt': 'nt',
    'trig': 'trig',
    'json-ld': 'json',
    # Available but not activated
    # 'nquads': 'nq',
    # 'trix': 'trix',
}

# Includes control characters, unicode surrogate characters and unicode end-of-plane non-characters
ILLEGAL_XML_CHARS = '[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]'


def guess_format(string):
    '''Guess format given an extension or a mime-type'''
    if string in ACCEPTED_MIME_TYPES:
        return ACCEPTED_MIME_TYPES[string]
    return raw_guess_format(string, FORMAT_MAP)


def negociate_content(default='json-ld'):
    '''Perform a content negociation on the format given the Accept header'''
    mimetype = request.accept_mimetypes.best_match(ACCEPTED_MIME_TYPES.keys())
    return ACCEPTED_MIME_TYPES.get(mimetype, default)


def want_rdf():
    '''Check wether client prefer RDF over the default HTML'''
    mimetype = request.accept_mimetypes.best
    return mimetype in ACCEPTED_MIME_TYPES


# JSON-LD context used for udata DCAT representation
CONTEXT = {
    # Namespaces
    '@vocab': 'http://www.w3.org/ns/dcat#',
    'dcat': 'http://www.w3.org/ns/dcat#',
    'dct': 'http://purl.org/dc/terms/',
    'foaf': 'http://xmlns.com/foaf/0.1/',
    'org': 'http://www.w3.org/ns/org#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'spdx': 'http://spdx.org/rdf/terms#',
    'vcard': 'http://www.w3.org/2006/vcard/ns#',
    'schema': 'http://schema.org/',
    'hydra': 'http://www.w3.org/ns/hydra/core#',
    'freq': 'http://purl.org/cld/freq/',
    # Aliased field
    'downloadURL': {
        '@id': 'dcat:downloadURL',
        '@type': '@id'
    },
    'accessURL': {
        '@id': 'dcat:accessURL',
        '@type': '@id'
    },
    'dataset': {
        '@id': 'dcat:dataset',
        '@type': '@id'
    },
    'distribution': {
        '@id': 'dcat:distribution',
        '@type': '@id'
    },
    'title': 'dct:title',
    'description': 'dct:description',
    'issued': {
        '@id': 'dct:issued',
        '@type': 'http://www.w3.org/2001/XMLSchema#dateTime'
    },
    'modified': {
        '@id': 'dct:modified',
        '@type': 'http://www.w3.org/2001/XMLSchema#dateTime'
    },
    'language': 'dct:language',
    'license': 'dct:license',
    'rights': 'dct:rights',
    'spatial': 'dct:spatial',
    'identifier': 'dct:identifier',
    'temporal': 'dct:temporal',
    'format': 'dct:format',
    'accrualPeriodicity': 'dct:accrualPeriodicity',
    'homepage': {
        '@id': 'foaf:homepage',
        '@type': '@id'
    },
    'publisher': {
        '@id': 'dct:publisher',
        '@type': '@id'
    },
    'fn': 'vcard:fn',
    'hasEmail': 'vcard:email',
    'subOrganizationOf': 'org:subOrganizationOf',
    'checksum': 'spdx:checksum',
    'algorithm': {
        '@id': 'spdx:algorithm',
        '@type': '@id'
    },
    'checksumValue': 'spdx:checksumValue',
    'label': 'rdfs:label',
    'name': 'foaf:name',
    'startDate': 'schema:startDate',
    'endDate': 'schema:endDate',
    'view': {
        '@id': 'hydra:view',
        '@type': '@id'
    },
    'first': {
        '@id': 'hydra:first',
        '@type': '@id'
    },
    'last': {
        '@id': 'hydra:last',
        '@type': '@id'
    },
    'next': {
        '@id': 'hydra:next',
        '@type': '@id'
    },
    'previous': {
        '@id': 'hydra:previous',
        '@type': '@id'
    },
    'totalItems': 'hydra:totalItems',
}


def url_from_rdf(rdf, prop):
    '''
    Try to extract An URL from a resource property.
    It can be expressed in many forms as a URIRef or a Literal
    '''
    value = rdf.value(prop)
    if isinstance(value, (URIRef, Literal)):
        return value.toPython()
    elif isinstance(value, RdfResource):
        return value.identifier.toPython()


def escape_xml_illegal_chars(val, replacement='?'):
    illegal_xml_chars_RE = re.compile(ILLEGAL_XML_CHARS)
    return illegal_xml_chars_RE.sub(replacement, val)


def paginate_catalog(catalog, graph, datasets, format, rdf_catalog_endpoint, **values):
    if not format:
        raise ValueError('Pagination requires format')
    catalog.add(RDF.type, HYDRA.Collection)
    catalog.set(HYDRA.totalItems, Literal(datasets.total))
    kwargs = {
        'format': format,
        'page_size': datasets.page_size,
        '_external': True,
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
    '''
    Return a proper flask response for a RDF resource given an expected format.
    '''
    fmt = guess_format(format)
    if not fmt:
        abort(404)
    headers = {
        'Content-Type': RDF_MIME_TYPES[fmt]
    }
    kwargs = {}
    if fmt == 'json-ld':
        kwargs['context'] = CONTEXT
    if isinstance(graph, RdfResource):
        graph = graph.graph
    return escape_xml_illegal_chars(graph.serialize(format=fmt, **kwargs)), 200, headers
