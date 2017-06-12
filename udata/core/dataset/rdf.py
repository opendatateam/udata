# -*- coding: utf-8 -*-
from __future__ import unicode_literals
'''
This module centralize dataset helpers for RDF/DCAT serialization and parsing
'''
import calendar
import html2text

from datetime import date
from HTMLParser import HTMLParser
from dateutil.parser import parse as parse_dt
from flask import url_for
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.resource import Resource as RdfResource
from rdflib.namespace import RDF

from udata.models import db
from udata.core.organization.rdf import organization_to_rdf
from udata.core.user.rdf import user_to_rdf
from udata.rdf import DCAT, DCT, SCV, SPDX, SCHEMA, namespace_manager
from udata.utils import get_by

from .models import Dataset, Resource, Checksum, License


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
    text = text.toPython() if isinstance(text, Literal) else ''
    if is_html(text):
        return html2text.html2text(text.strip(), bodywidth=0).strip()
    else:
        return text.strip()


def temporal_to_rdf(daterange, graph=None):
    if not daterange:
        return
    graph = graph or Graph(namespace_manager=namespace_manager)
    pot = graph.resource(BNode())
    pot.set(RDF.type, DCT.PeriodOfTime)
    pot.set(SCHEMA.startDate, Literal(daterange.start.date()))
    pot.set(SCHEMA.endDate, Literal(daterange.end.date()))
    return pot


def resource_to_rdf(resource, dataset=None, graph=None):
    '''
    Map a Resource domain model to a DCAT/RDF graph
    '''
    graph = graph or Graph(namespace_manager=namespace_manager)
    if dataset and dataset.id:
        id = URIRef(url_for('datasets.show_redirect', dataset=dataset.id,
                            _external=True,
                            _anchor='resource-{0}'.format(resource.id)))
    else:
        id = BNode(resource.id)
    permalink = url_for('datasets.resource', id=resource.id, _external=True)
    r = graph.resource(id)
    r.set(RDF.type, DCAT.Distribution)
    r.add(DCT.title, Literal(resource.title))
    r.add(DCT.description, Literal(resource.description))
    r.add(DCAT.downloadURL, URIRef(resource.url))
    r.add(DCAT.accessURL, URIRef(permalink))
    r.add(DCT.issued, Literal(resource.published))
    r.add(DCT.modified, Literal(resource.modified))
    if dataset and dataset.license:
        r.add(DCT.rights, Literal(dataset.license.title))
        if dataset.license.url:
            r.add(DCT.license, URIRef(dataset.license.url))
    if resource.filesize is not None:
        r.add(DCAT.bytesSize, Literal(resource.filesize))
    if resource.mime:
        r.add(DCAT.mediaType, Literal(resource.mime))
    if resource.format:
        r.add(DCT.term('format'), Literal(resource.format))
    if resource.checksum:
        checksum = graph.resource(BNode())
        checksum.set(RDF.type, SPDX.Checksum)
        algorithm = 'checksumAlgorithm_{0}'.format(resource.checksum.type)
        checksum.add(SPDX.algorithm, getattr(SPDX, algorithm))
        checksum.add(SPDX.checksumValue, Literal(resource.checksum.value))
        r.add(SPDX.checksum, checksum)
    return r


def dataset_to_rdf(dataset, graph=None):
    '''
    Map a dataset domain model to a DCAT/RDF graph
    '''
    # Use the unlocalized permalink to the dataset as URI when available
    # unless there is already an upstream URI
    if 'uri' in dataset.extras:
        id = URIRef(dataset.extras['uri'])
    elif dataset.id:
        id = URIRef(url_for('datasets.show_redirect',
                            dataset=dataset.id,
                            _external=True))
    else:
        id = BNode()
    # Expose upstream identifier if present
    if 'dct:identifier' in dataset.extras:
        identifier = dataset.extras['dct:identifier']
    else:
        identifier = dataset.id
    graph = graph or Graph(namespace_manager=namespace_manager)
    d = graph.resource(id)
    d.add(RDF.type, DCAT.Dataset)
    d.add(DCT.identifier, Literal(identifier))
    d.add(DCT.title, Literal(dataset.title))
    d.add(DCT.description, Literal(dataset.description))
    d.add(DCT.issued, Literal(dataset.created_at))
    d.add(DCT.modified, Literal(dataset.last_modified))
    for tag in dataset.tags:
        d.add(DCAT.keyword, Literal(tag))

    for resource in dataset.resources:
        d.add(DCAT.distribution, resource_to_rdf(resource, dataset, graph))

    if dataset.owner:
        d.add(DCT.publisher, user_to_rdf(dataset.owner, graph))
    elif dataset.organization:
        d.add(DCT.publisher, organization_to_rdf(dataset.organization, graph))

    if dataset.temporal_coverage:
        d.add(DCT.temporal, temporal_to_rdf(dataset.temporal_coverage, graph))

    return d


CHECKSUM_ALGORITHMS = {
    SPDX.checksumAlgorithm_md5: 'md5',
    SPDX.checksumAlgorithm_sha1: 'sha1',
    SPDX.checksumAlgorithm_sha256: 'sha256',
}


def rdf_value(obj, predicate, default=None):
    value = obj.value(predicate)
    return value.toPython() if value else default


def temporal_from_literal(text):
    '''
    Parse a temporal coverage from a literal ie. either:
    - an ISO date range
    - a single ISO date period (month,year)
    '''
    if text.count('/') == 1:
        # This is an ISO date range as preconized by Gov.uk
        # http://guidance.data.gov.uk/dcat_fields.html
        start, end = text.split('/')
        return db.DateRange(
            start=parse_dt(start).date(),
            end=parse_dt(end).date()
        )
    else:
        separators = text.count('-')
        if separators == 0:
            # this is a year
            return db.DateRange(
                start=date(int(text), 1, 1),
                end=date(int(text), 12, 31)
            )
        elif separators == 1:
            # this is a month
            dt = parse_dt(text).date()
            return db.DateRange(
                start=dt.replace(day=1),
                end=dt.replace(day=calendar.monthrange(dt.year, dt.month)[1])
            )


def temporal_from_resource(resource):
    '''
    Parse a temporal coverage from a RDF class/resource ie. either:
    - a `dct:PeriodOfTime` with schema.org `startDate` and `endDate` properties
    - an inline gov.uk Time Interval value
    - an URI reference to a gov.uk Time Interval ontology
      http://reference.data.gov.uk/
    '''
    if isinstance(resource.identifier, URIRef):
        # Fetch remote ontology if necessary
        g = Graph().parse(str(resource.identifier))
        resource = g.resource(resource.identifier)
    if resource.value(SCHEMA.startDate):
        return db.DateRange(
            start=resource.value(SCHEMA.startDate).toPython(),
            end=resource.value(SCHEMA.endDate).toPython()
        )
    elif resource.value(SCV.min):
        return db.DateRange(
            start=resource.value(SCV.min).toPython(),
            end=resource.value(SCV.max).toPython()
        )


def temporal_from_rdf(period_of_time):
    '''Parse an temporal coverage'''
    if isinstance(period_of_time, Literal):
        return temporal_from_literal(str(period_of_time))
    elif isinstance(period_of_time, RdfResource):
        return temporal_from_resource(period_of_time)


def resource_from_rdf(graph_or_distrib, dataset=None):
    '''
    Map a Resource domain model to a DCAT/RDF graph
    '''
    if isinstance(graph_or_distrib, RdfResource):
        distrib = graph_or_distrib
    else:
        node = graph_or_distrib.value(predicate=RDF.type,
                                      object=DCAT.Distribution)
        distrib = graph_or_distrib.resource(node)

    download_url = distrib.value(DCAT.downloadURL)
    access_url = distrib.value(DCAT.accessURL)
    url = str(download_url or access_url)

    if dataset:
        resource = get_by(dataset.resources, 'url', url)
    if not dataset or not resource:
        resource = Resource()
        if dataset:
            dataset.resources.append(resource)
    resource.title = rdf_value(distrib, DCT.title)
    resource.url = url
    resource.description = sanitize_html(distrib.value(DCT.description))
    resource.filesize = rdf_value(distrib, DCAT.bytesSize)
    resource.mime = rdf_value(distrib, DCAT.mediaType)
    fmt = rdf_value(distrib, DCT.term('format'))
    if fmt:
        resource.format = fmt.lower()
    checksum = distrib.value(SPDX.checksum)
    if checksum:
        algorithm = checksum.value(SPDX.algorithm).identifier
        algorithm = CHECKSUM_ALGORITHMS.get(algorithm)
        if algorithm:
            resource.checksum = Checksum()
            resource.checksum.value = rdf_value(checksum, SPDX.checksumValue)
            resource.checksum.type = algorithm

    resource.published = rdf_value(distrib, DCT.issued, resource.published)
    resource.modified = rdf_value(distrib, DCT.modified, resource.modified)

    return resource


def dataset_from_rdf(graph, dataset=None):
    '''
    Create or update a dataset from a RDF/DCAT graph
    '''
    dataset = dataset or Dataset()

    node = graph.value(predicate=RDF.type, object=DCAT.Dataset)
    d = graph.resource(node)

    dataset.title = rdf_value(d, DCT.title)

    dataset.description = sanitize_html(d.value(DCT.description))

    tags = [tag.toPython() for tag in d.objects(DCAT.keyword)]
    tags += [theme.toPython() for theme in d.objects(DCAT.theme)]
    dataset.tags = list(set(tags))

    dataset.extras['dct:identifier'] = rdf_value(d, DCT.identifier)

    if isinstance(d.identifier, URIRef):
        dataset.extras['uri'] = d.identifier.toPython()

    dataset.temporal_coverage = temporal_from_rdf(d.value(DCT.temporal))

    licenses = set()
    for distrib in d.objects(DCAT.distribution):
        resource_from_rdf(distrib, dataset)
        for predicate in DCT.license, DCT.rights:
            value = distrib.value(predicate)
            if isinstance(value, (URIRef, Literal)):
                licenses.add(value.toPython())
            elif isinstance(value, RdfResource):
                licenses.add(value.identifier.toPython())

    for text in licenses:
        license = License.guess(text)
        if license:
            dataset.license = license
            break

    return dataset
