# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from rdflib import Graph
from rdflib.namespace import Namespace, NamespaceManager, DCTERMS, SKOS, FOAF, OWL, XSD

# Extra Namespaces
ADMS = Namespace("http://www.w3.org/ns/adms#")
DCAT = Namespace('http://www.w3.org/ns/dcat#')
HYDRA = Namespace('http://www.w3.org/ns/hydra/core#')
SCHEMA = Namespace('http://schema.org/')
SPDX = Namespace('http://spdx.org/rdf/terms#')
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
DCT = DCTERMS  # More common usage

namespace_manager = NamespaceManager(Graph())
namespace_manager.bind('foaf', FOAF)
namespace_manager.bind('dct', DCT)
namespace_manager.bind('skos', SKOS)
namespace_manager.bind('dcat', DCAT)
namespace_manager.bind('foaf', FOAF)
namespace_manager.bind('hydra', HYDRA)
namespace_manager.bind('vcard', VCARD)
namespace_manager.bind('owl', OWL)
namespace_manager.bind('xsd', XSD)

# RDF context used for udata DCAT repsentation
# CONTEXT = {
#     # Namespaces
#     "dcat": "http://www.w3.org/ns/dcat#",
#     "org": "http://www.w3.org/ns/org#",
#     "vcard": "http://www.w3.org/2006/vcard/ns#",
#     "foaf": "http://xmlns.com/foaf/0.1/",
#     "@vocab": "http://www.w3.org/ns/dcat#",
#     "dc": "http://purl.org/dc/terms/",
#     "pod": "https://project-open-data.cio.gov/v1.1/schema#",
#     "skos": "http://www.w3.org/2004/02/skos/core#",
#     # Aliased field
#     "describedBy": {
#         "@id": "http://www.w3.org/2007/05/powder#describedby",
#         "@type": "@id"
#     },
#     "downloadURL": {
#         "@id": "dcat:downloadURL",
#         "@type": "@id"
#     },
#     "accessURL": {
#         "@id": "dcat:accessURL",
#         "@type": "@id"
#     },
#     "title": "dc:title",
#     "description": "dc:description",
#     "issued": {
#         "@id": "dc:issued",
#         "@type": "http://www.w3.org/2001/XMLSchema#dateTime"
#     },
#     "modified": {
#         "@id": "dc:modified",
#         "@type": "http://www.w3.org/2001/XMLSchema#dateTime"
#     },
#     "language": "dc:language",
#     "license": "dc:license",
#     "rights": "dc:rights",
#     "spatial": "dc:spatial",
#     "conformsTo": {
#         "@id": "dc:conformsTo",
#         "@type": "@id"
#     },
#     "publisher": "dc:publisher",
#     "identifier": "dc:identifier",
#     "temporal": "dc:temporal",
#     "format": "dc:format",
#     "accrualPeriodicity": "dc:accrualPeriodicity",
#     "homepage": "foaf:homepage",
#     "accessLevel": "pod:accessLevel",
#     "bureauCode": "pod:bureauCode",
#     "dataQuality": "pod:dataQuality",
#     "describedByType": "pod:describedByType",
#     "primaryITInvestmentUII": "pod:primaryITInvestmentUII",
#     "programCode": "pod:programCode",
#     "fn": "vcard:fn",
#     "hasEmail": "vcard:email",
#     "name": "skos:prefLabel",
#     "subOrganizationOf": "org:subOrganizationOf"
# }
