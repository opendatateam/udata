'''
This module centralize dataset helpers for RDF/DCAT serialization and parsing
'''
import calendar
import logging

from datetime import date
from html.parser import HTMLParser
from dateutil.parser import parse as parse_dt
from flask import current_app
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.resource import Resource as RdfResource
from rdflib.namespace import RDF

from udata import i18n, uris
from udata.frontend.markdown import parse_html
from udata.models import db
from udata.rdf import (
    DCAT, DCT, FREQ, SCV, SKOS, SPDX, SCHEMA, EUFREQ,
    namespace_manager, url_from_rdf
)
from udata.utils import get_by, safe_unicode
from udata.uris import endpoint_for

from .models import Dataset, Resource, Checksum, License

log = logging.getLogger(__name__)

# Map extra frequencies (ie. not defined in Dublin Core) to closest equivalent
RDF_FREQUENCIES = {
    'punctual': None,
    'hourly': FREQ.continuous,
    'fourTimesADay': FREQ.daily,
    'threeTimesADay': FREQ.daily,
    'semidaily': FREQ.daily,
    'fourTimesAWeek': FREQ.threeTimesAWeek,
    'quinquennial': None,
    'unknown': None,
}

# Map european frequencies to their closest equivalent
# See:
#  - http://publications.europa.eu/mdr/resource/authority/frequency/html/frequencies-eng.html # noqa: E501
#  - https://publications.europa.eu/en/web/eu-vocabularies/at-dataset/-/resource/dataset/frequency # noqa: E501
EU_RDF_REQUENCIES = {
    # Match Dublin Core name
    EUFREQ.ANNUAL: 'annual',
    EUFREQ.BIENNIAL: 'biennial',
    EUFREQ.TRIENNIAL: 'triennial',
    EUFREQ.QUARTERLY: 'quarterly',
    EUFREQ.MONTHLY: 'monthly',
    EUFREQ.BIMONTHLY: 'bimonthly',
    EUFREQ.WEEKLY: 'weekly',
    EUFREQ.BIWEEKLY: 'biweekly',
    EUFREQ.DAILY: 'daily',
    # Name differs from Dublin Core
    EUFREQ.ANNUAL_2: 'semiannual',
    EUFREQ.ANNUAL_3: 'threeTimesAYear',
    EUFREQ.MONTHLY_2: 'semimonthly',
    EUFREQ.MONTHLY_3: 'threeTimesAMonth',
    EUFREQ.WEEKLY_2: 'semiweekly',
    EUFREQ.WEEKLY_3: 'threeTimesAWeek',
    EUFREQ.DAILY_2: 'semidaily',
    EUFREQ.CONT: 'continuous',
    EUFREQ.UPDATE_CONT: 'continuous',
    EUFREQ.IRREG: 'irregular',
    EUFREQ.UNKNOWN: 'unknown',
    EUFREQ.OTHER: 'unknown',
    EUFREQ.NEVER: 'punctual',
}


Dataset.extras.register('uri', db.StringField)
Dataset.extras.register('dct:identifier', db.StringField)


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
        return parse_html(text)
    else:
        return text.strip()


def temporal_to_rdf(daterange, graph=None):
    if not daterange:
        return
    graph = graph or Graph(namespace_manager=namespace_manager)
    pot = graph.resource(BNode())
    pot.set(RDF.type, DCT.PeriodOfTime)
    pot.set(SCHEMA.startDate, Literal(daterange.start))
    pot.set(SCHEMA.endDate, Literal(daterange.end))
    return pot


def frequency_to_rdf(frequency, graph=None):
    if not frequency:
        return
    return RDF_FREQUENCIES.get(frequency, getattr(FREQ, frequency))


def resource_to_rdf(resource, dataset=None, graph=None):
    '''
    Map a Resource domain model to a DCAT/RDF graph
    '''
    graph = graph or Graph(namespace_manager=namespace_manager)
    if dataset and dataset.id:
        id = URIRef(endpoint_for('datasets.show_redirect', 'api.dataset', dataset=dataset.id,
                            _external=True,
                            _anchor='resource-{0}'.format(resource.id)))
    else:
        id = BNode(resource.id)
    permalink = endpoint_for('datasets.resource', 'api.resource_redirect', id=resource.id, _external=True)
    r = graph.resource(id)
    r.set(RDF.type, DCAT.Distribution)
    r.set(DCT.identifier, Literal(resource.id))
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
        id = URIRef(endpoint_for('datasets.show_redirect', 'api.dataset', 
                    dataset=dataset.id, _external=True))
    else:
        id = BNode()
    # Expose upstream identifier if present
    if 'dct:identifier' in dataset.extras:
        identifier = dataset.extras['dct:identifier']
    else:
        identifier = dataset.id
    graph = graph or Graph(namespace_manager=namespace_manager)

    d = graph.resource(id)
    d.set(RDF.type, DCAT.Dataset)
    d.set(DCT.identifier, Literal(identifier))
    d.set(DCT.title, Literal(dataset.title))
    d.set(DCT.description, Literal(dataset.description))
    d.set(DCT.issued, Literal(dataset.created_at))
    d.set(DCT.modified, Literal(dataset.last_modified))

    if dataset.acronym:
        d.set(SKOS.altLabel, Literal(dataset.acronym))

    for tag in dataset.tags:
        d.add(DCAT.keyword, Literal(tag))

    for resource in dataset.resources:
        d.add(DCAT.distribution, resource_to_rdf(resource, dataset, graph))

    if dataset.temporal_coverage:
        d.set(DCT.temporal, temporal_to_rdf(dataset.temporal_coverage, graph))

    frequency = frequency_to_rdf(dataset.frequency)
    if frequency:
        d.set(DCT.accrualPeriodicity, frequency)

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
    '''Failsafe parsing of a temporal coverage'''
    try:
        if isinstance(period_of_time, Literal):
            return temporal_from_literal(str(period_of_time))
        elif isinstance(period_of_time, RdfResource):
            return temporal_from_resource(period_of_time)
    except Exception:
        # There are a lot of cases where parsing could/should fail
        # but we never want to break the whole dataset parsing
        # so we log the error for future investigation and improvement
        log.warning('Unable to parse temporal coverage', exc_info=True)


def frequency_from_rdf(term):
    if isinstance(term, str):
        try:
            term = URIRef(uris.validate(term))
        except uris.ValidationError:
            pass
    if isinstance(term, RdfResource):
        term = term.identifier
    if isinstance(term, URIRef):
        if EUFREQ in term:
            return EU_RDF_REQUENCIES.get(term)
        _, _, freq = namespace_manager.compute_qname(term)
        return freq


def title_from_rdf(rdf, url):
    '''
    Try to extract a distribution title from a property.
    As it's not a mandatory property,
    it fallback on building a title from the URL
    then the format and in last ressort a generic resource name.
    '''
    title = rdf_value(rdf, DCT.title)
    if title:
        return title
    if url:
        last_part = url.split('/')[-1]
        if '.' in last_part and '?' not in last_part:
            return last_part
    fmt = rdf_value(rdf, DCT.term('format'))
    lang = current_app.config['DEFAULT_LANGUAGE']
    with i18n.language(lang):
        if fmt:
            return i18n._('{format} resource').format(format=fmt.lower())
        else:
            return i18n._('Nameless resource')


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

    download_url = url_from_rdf(distrib, DCAT.downloadURL)
    access_url = url_from_rdf(distrib, DCAT.accessURL)
    url = safe_unicode(download_url or access_url)

    if dataset:
        resource = get_by(dataset.resources, 'url', url)
    if not dataset or not resource:
        resource = Resource()
        if dataset:
            dataset.resources.append(resource)
    resource.title = title_from_rdf(distrib, url)
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

    identifier = rdf_value(distrib, DCT.identifier)
    if identifier:
        resource.extras['dct:identifier'] = identifier

    if isinstance(distrib.identifier, URIRef):
        resource.extras['uri'] = distrib.identifier.toPython()

    return resource


def dataset_from_rdf(graph, dataset=None, node=None):
    '''
    Create or update a dataset from a RDF/DCAT graph
    '''
    dataset = dataset or Dataset()

    if node is None:  # Assume first match is the only match
        node = graph.value(predicate=RDF.type, object=DCAT.Dataset)

    d = graph.resource(node)

    dataset.title = rdf_value(d, DCT.title)
    dataset.description = sanitize_html(d.value(DCT.description))
    dataset.frequency = frequency_from_rdf(d.value(DCT.accrualPeriodicity))

    acronym = rdf_value(d, SKOS.altLabel)
    if acronym:
        dataset.acronym = acronym

    tags = [tag.toPython() for tag in d.objects(DCAT.keyword)]
    tags += [theme.toPython() for theme in d.objects(DCAT.theme)]
    dataset.tags = list(set(tags))

    identifier = rdf_value(d, DCT.identifier)
    if identifier:
        dataset.extras['dct:identifier'] = identifier

    if isinstance(d.identifier, URIRef):
        dataset.extras['uri'] = d.identifier.toPython()

    dataset.temporal_coverage = temporal_from_rdf(d.value(DCT.temporal))

    licenses = set()
    for distrib in d.objects(DCAT.distribution | DCAT.distributions):
        resource_from_rdf(distrib, dataset)
        for predicate in DCT.license, DCT.rights:
            value = distrib.value(predicate)
            if isinstance(value, (URIRef, Literal)):
                licenses.add(value.toPython())
            elif isinstance(value, RdfResource):
                licenses.add(value.identifier.toPython())

    default_license = dataset.license or License.default()
    dataset_license = rdf_value(d, DCT.license)
    dataset.license = License.guess(dataset_license, *licenses, default=default_license)

    return dataset
