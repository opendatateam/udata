# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date

from flask import url_for

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, FOAF
from rdflib.resource import Resource as RdfResource

from udata.models import db
from udata.core.dataset.models import Dataset, Resource, License, Checksum
from udata.core.dataset.factories import (
    DatasetFactory, ResourceFactory, LicenseFactory
)
from udata.core.dataset.rdf import (
    dataset_to_rdf, dataset_from_rdf, resource_to_rdf, resource_from_rdf,
    temporal_from_rdf, frequency_to_rdf
)
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.rdf import DCAT, DCT, FREQ, SPDX, SCHEMA, SKOS
from udata.tests import TestCase, DBTestMixin
from udata.tests.frontend import FrontTestCase
from udata.utils import faker


class DatasetToRdfTest(FrontTestCase):
    modules = ['core.dataset', 'core.organization', 'core.user', 'core.site']

    def test_minimal(self):
        dataset = DatasetFactory.build()  # Does not have an URL
        d = dataset_to_rdf(dataset)
        g = d.graph

        self.assertIsInstance(d, RdfResource)
        self.assertEqual(len(list(g.subjects(RDF.type, DCAT.Dataset))), 1)

        self.assertEqual(g.value(d.identifier, RDF.type), DCAT.Dataset)

        self.assertIsInstance(d.identifier, BNode)
        self.assertEqual(d.value(DCT.identifier), Literal(dataset.id))
        self.assertEqual(d.value(DCT.title), Literal(dataset.title))
        self.assertEqual(d.value(DCT.issued), Literal(dataset.created_at))
        self.assertEqual(d.value(DCT.modified),
                         Literal(dataset.last_modified))

    def test_all_dataset_fields(self):
        resources = ResourceFactory.build_batch(3)
        dataset = DatasetFactory(tags=faker.words(nb=3), resources=resources,
                                 frequency='daily', acronym='acro')
        d = dataset_to_rdf(dataset)
        g = d.graph

        self.assertIsInstance(d, RdfResource)
        self.assertEqual(len(list(g.subjects(RDF.type, DCAT.Dataset))), 1)

        self.assertEqual(g.value(d.identifier, RDF.type), DCAT.Dataset)

        self.assertIsInstance(d.identifier, URIRef)
        uri = url_for('datasets.show_redirect',
                      dataset=dataset.id, _external=True)
        self.assertEqual(str(d.identifier), uri)
        self.assertEqual(d.value(DCT.identifier), Literal(dataset.id))
        self.assertEqual(d.value(DCT.title), Literal(dataset.title))
        self.assertEqual(d.value(SKOS.altLabel), Literal(dataset.acronym))
        self.assertEqual(d.value(DCT.description),
                         Literal(dataset.description))
        self.assertEqual(d.value(DCT.issued), Literal(dataset.created_at))
        self.assertEqual(d.value(DCT.modified),
                         Literal(dataset.last_modified))
        self.assertEqual(d.value(DCT.accrualPeriodicity).identifier,
                         FREQ.daily)
        expected_tags = set(Literal(t) for t in dataset.tags)
        self.assertEqual(set(d.objects(DCAT.keyword)), expected_tags)

        self.assertEqual(len(list(d.objects(DCAT.distribution))),
                         len(resources))

    def test_map_unkownn_frequencies(self):
        self.assertEqual(frequency_to_rdf('hourly'), FREQ.continuous)

        self.assertEqual(frequency_to_rdf('fourTimesADay'), FREQ.daily)
        self.assertEqual(frequency_to_rdf('threeTimesADay'), FREQ.daily)
        self.assertEqual(frequency_to_rdf('semidaily'), FREQ.daily)

        self.assertEqual(frequency_to_rdf('fourTimesAWeek'),
                         FREQ.threeTimesAWeek)

        self.assertIsNone(frequency_to_rdf('punctual'))
        self.assertIsNone(frequency_to_rdf('unknown'))

        self.assertIsNone(frequency_to_rdf('quinquennial'))  # Better idea ?

    def test_minimal_resource_fields(self):
        resource = ResourceFactory()

        r = resource_to_rdf(resource)
        graph = r.graph
        distribs = graph.subjects(RDF.type, DCAT.Distribution)

        self.assertIsInstance(r, RdfResource)
        self.assertEqual(len(list(distribs)), 1)

        self.assertEqual(graph.value(r.identifier, RDF.type),
                         DCAT.Distribution)
        self.assertEqual(r.value(DCT.title), Literal(resource.title))
        self.assertEqual(r.value(DCAT.downloadURL).identifier,
                         URIRef(resource.url))
        self.assertEqual(r.value(DCT.issued), Literal(resource.published))
        self.assertEqual(r.value(DCT.modified), Literal(resource.modified))

    def test_all_resource_fields(self):
        license = LicenseFactory()
        resource = ResourceFactory(format='csv')
        dataset = DatasetFactory(resources=[resource], license=license)
        permalink = url_for('datasets.resource',
                            id=resource.id,
                            _external=True)

        r = resource_to_rdf(resource, dataset)

        self.assertEqual(r.value(DCT.title), Literal(resource.title))
        self.assertEqual(r.value(DCT.description),
                         Literal(resource.description))
        self.assertEqual(r.value(DCT.issued), Literal(resource.published))
        self.assertEqual(r.value(DCT.modified), Literal(resource.modified))
        self.assertEqual(r.value(DCT.license).identifier, URIRef(license.url))
        self.assertEqual(r.value(DCT.rights), Literal(license.title))
        self.assertEqual(r.value(DCAT.downloadURL).identifier,
                         URIRef(resource.url))
        self.assertEqual(r.value(DCAT.accessURL).identifier, URIRef(permalink))
        self.assertEqual(r.value(DCAT.bytesSize), Literal(resource.filesize))
        self.assertEqual(r.value(DCAT.mediaType), Literal(resource.mime))
        self.assertEqual(r.value(DCT.term('format')), Literal(resource.format))

        checksum = r.value(SPDX.checksum)
        self.assertEqual(r.graph.value(checksum.identifier, RDF.type),
                         SPDX.Checksum)
        self.assertEqual(r.graph.value(checksum.identifier, SPDX.algorithm),
                         SPDX.checksumAlgorithm_sha1)
        self.assertEqual(checksum.value(SPDX.checksumValue),
                         Literal(resource.checksum.value))

    def test_with_org(self):
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        d = dataset_to_rdf(dataset)
        g = d.graph

        self.assertIsInstance(d, RdfResource)
        datasets = g.subjects(RDF.type, DCAT.Dataset)
        organizations = g.subjects(RDF.type, FOAF.Organization)
        self.assertEqual(len(list(datasets)), 1)
        self.assertEqual(len(list(organizations)), 1)

        publisher = d.value(DCT.publisher)
        self.assertEqual(publisher.value(RDF.type).identifier,
                         FOAF.Organization)

    def test_with_owner(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        d = dataset_to_rdf(dataset)
        g = d.graph

        self.assertIsInstance(d, RdfResource)
        datasets = g.subjects(RDF.type, DCAT.Dataset)
        users = g.subjects(RDF.type, FOAF.Person)
        self.assertEqual(len(list(datasets)), 1)
        self.assertEqual(len(list(users)), 1)

        publisher = d.value(DCT.publisher)
        self.assertEqual(publisher.value(RDF.type).identifier,
                         FOAF.Person)

    def test_temporal_coverage(self):
        start = faker.past_date(start_date='-30d')
        end = faker.future_date(end_date='+30d')
        temporal_coverage = db.DateRange(start=start, end=end)
        dataset = DatasetFactory(temporal_coverage=temporal_coverage)

        d = dataset_to_rdf(dataset)

        pot = d.value(DCT.temporal)

        self.assertEqual(pot.value(RDF.type).identifier, DCT.PeriodOfTime)
        self.assertEqual(pot.value(SCHEMA.startDate).toPython(), start)
        self.assertEqual(pot.value(SCHEMA.endDate).toPython(), end)

    def test_from_external_repository(self):
        dataset = DatasetFactory(extras={
            'dct:identifier': 'an-identifier',
            'uri': 'https://somewhere.org/dataset',
        })

        d = dataset_to_rdf(dataset)

        self.assertIsInstance(d.identifier, URIRef)
        self.assertEqual(str(d.identifier), 'https://somewhere.org/dataset')
        self.assertEqual(d.value(DCT.identifier), Literal('an-identifier'))


class RdfToDatasetTest(DBTestMixin, TestCase):
    def test_minimal(self):
        node = BNode()
        g = Graph()

        title = faker.sentence()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(title)))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(dataset.title, title)

    def test_update(self):
        original = DatasetFactory()

        node = URIRef('https://test.org/dataset')
        g = Graph()

        new_title = faker.sentence()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(new_title)))

        dataset = dataset_from_rdf(g, dataset=original)
        dataset.validate()

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(dataset.id, original.id)
        self.assertEqual(dataset.title, new_title)

    def test_all_fields(self):
        uri = 'https://test.org/dataset'
        node = URIRef(uri)
        g = Graph()

        id = faker.uuid4()
        title = faker.sentence()
        acronym = faker.word()
        description = faker.paragraph()
        tags = faker.words(nb=3)
        start = faker.past_date(start_date='-30d')
        end = faker.future_date(end_date='+30d')
        g.set((node, RDF.type, DCAT.Dataset))
        g.set((node, DCT.identifier, Literal(id)))
        g.set((node, DCT.title, Literal(title)))
        g.set((node, SKOS.altLabel, Literal(acronym)))
        g.set((node, DCT.description, Literal(description)))
        g.set((node, DCT.accrualPeriodicity, FREQ.daily))
        pot = BNode()
        g.add((node, DCT.temporal, pot))
        g.set((pot, RDF.type, DCT.PeriodOfTime))
        g.set((pot, SCHEMA.startDate, Literal(start)))
        g.set((pot, SCHEMA.endDate, Literal(end)))
        for tag in tags:
            g.add((node, DCAT.keyword, Literal(tag)))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(dataset.title, title)
        self.assertEqual(dataset.acronym, acronym)
        self.assertEqual(dataset.description, description)
        self.assertEqual(dataset.frequency, 'daily')
        self.assertEqual(set(dataset.tags), set(tags))
        self.assertIsInstance(dataset.temporal_coverage, db.DateRange)
        self.assertEqual(dataset.temporal_coverage.start, start)
        self.assertEqual(dataset.temporal_coverage.end, end)

        extras = dataset.extras
        self.assertIn('dct:identifier', extras)
        self.assertEqual(extras['dct:identifier'], id)
        self.assertIn('uri', extras)
        self.assertEqual(extras['uri'], uri)

    def test_html_description(self):
        node = BNode()
        g = Graph()

        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.identifier, Literal(faker.uuid4())))
        g.add((node, DCT.title, Literal(faker.sentence())))
        g.add((node, DCT.description, Literal('<div>a description</div>')))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(dataset.description, 'a description')

    def test_theme_and_tags(self):
        node = BNode()
        g = Graph()

        tags = faker.words(nb=3)
        themes = faker.words(nb=3)
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(faker.sentence())))
        for tag in tags:
            g.add((node, DCAT.keyword, Literal(tag)))
        for theme in themes:
            g.add((node, DCAT.theme, Literal(theme)))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(set(dataset.tags), set(tags + themes))

    def test_minimal_resource_fields(self):
        node = BNode()
        g = Graph()

        title = faker.sentence()
        url = faker.uri()
        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(title)))
        g.add((node, DCAT.downloadURL, Literal(url)))

        resource = resource_from_rdf(g)
        resource.validate()

        self.assertIsInstance(resource, Resource)
        self.assertEqual(resource.title, title)
        self.assertEqual(resource.url, url)

    def test_all_resource_fields(self):
        node = BNode()
        g = Graph()

        title = faker.sentence()
        url = faker.uri()
        description = faker.paragraph()
        filesize = faker.pyint()
        issued = faker.date_time_between(start_date='-60d', end_date='-30d')
        modified = faker.past_datetime(start_date='-30d')
        mime = faker.mime_type()
        sha1 = faker.sha1()

        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(title)))
        g.add((node, DCT.description, Literal(description)))
        g.add((node, DCAT.downloadURL, Literal(url)))
        g.add((node, DCT.issued, Literal(issued)))
        g.add((node, DCT.modified, Literal(modified)))
        g.add((node, DCAT.bytesSize, Literal(filesize)))
        g.add((node, DCAT.mediaType, Literal(mime)))
        g.add((node, DCT.term('format'), Literal('CSV')))

        checksum = BNode()
        g.add((node, SPDX.checksum, checksum))
        g.add((checksum, RDF.type, SPDX.Checksum))
        g.add((checksum, SPDX.algorithm, SPDX.checksumAlgorithm_sha1))
        g.add((checksum, SPDX.checksumValue, Literal(sha1)))

        resource = resource_from_rdf(g)
        resource.validate()

        self.assertIsInstance(resource, Resource)
        self.assertEqual(resource.title, title)
        self.assertEqual(resource.url, url)
        self.assertEqual(resource.description, description)
        self.assertEqual(resource.filesize, filesize)
        self.assertEqual(resource.mime, mime)
        self.assertIsInstance(resource.checksum, Checksum)
        self.assertEqual(resource.checksum.type, 'sha1')
        self.assertEqual(resource.checksum.value, sha1)
        self.assertEqual(resource.published, issued)
        self.assertEqual(resource.modified, modified)
        self.assertEqual(resource.format, 'csv')

    def test_download_url_over_access_url(self):
        node = BNode()
        g = Graph()

        access_url = faker.uri()
        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(faker.sentence())))
        g.add((node, DCAT.accessURL, Literal(access_url)))

        resource = resource_from_rdf(g)
        resource.validate()
        self.assertEqual(resource.url, access_url)

        download_url = faker.uri()
        g.add((node, DCAT.downloadURL, Literal(download_url)))

        resource = resource_from_rdf(g)
        resource.validate()
        self.assertEqual(resource.url, download_url)

    def test_resource_html_description(self):
        node = BNode()
        g = Graph()

        description = faker.paragraph()
        html_description = '<div>{0}</div>'.format(description)
        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(faker.sentence())))
        g.add((node, DCT.description, Literal(html_description)))
        g.add((node, DCAT.downloadURL, Literal(faker.uri())))

        resource = resource_from_rdf(g)
        resource.validate()

        self.assertEqual(resource.description, description)

    def test_resource_title_from_url(self):
        node = BNode()
        g = Graph()
        url = 'https://www.somewhere.com/somefile.csv'

        g.set((node, RDF.type, DCAT.Distribution))
        g.set((node, DCAT.downloadURL, URIRef(url)))

        resource = resource_from_rdf(g)
        resource.validate()

        self.assertEqual(resource.title, 'somefile.csv')

    def test_resource_title_from_format(self):
        node = BNode()
        g = Graph()
        url = 'https://www.somewhere.com/no-extension/'

        g.set((node, RDF.type, DCAT.Distribution))
        g.set((node, DCAT.downloadURL, URIRef(url)))
        g.set((node, DCT.term('format'), Literal('CSV')))

        resource = resource_from_rdf(g)
        resource.validate()

        self.assertEqual(resource.title, 'csv resource')

    def test_resource_generic_title(self):
        node = BNode()
        g = Graph()
        url = 'https://www.somewhere.com/no-extension/'

        g.set((node, RDF.type, DCAT.Distribution))
        g.set((node, DCAT.downloadURL, URIRef(url)))

        resource = resource_from_rdf(g)
        resource.validate()

        self.assertEqual(resource.title, 'Nameless resource')

    def test_resource_title_ignore_dynamic_url(self):
        node = BNode()
        g = Graph()
        url = 'https://www.somewhere.com/endpoint.json?param=value'

        g.set((node, RDF.type, DCAT.Distribution))
        g.set((node, DCAT.downloadURL, URIRef(url)))

        resource = resource_from_rdf(g)
        resource.validate()

        self.assertEqual(resource.title, 'Nameless resource')

    def test_match_existing_resource_by_url(self):
        dataset = DatasetFactory(resources=ResourceFactory.build_batch(3))
        existing_resource = dataset.resources[1]
        node = BNode()
        g = Graph()

        new_title = faker.sentence()
        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(new_title)))
        g.add((node, DCAT.downloadURL, Literal(existing_resource.url)))

        resource = resource_from_rdf(g, dataset)
        resource.validate()

        self.assertIsInstance(resource, Resource)
        self.assertEqual(resource.title, new_title)
        self.assertEqual(resource.id, existing_resource.id)

    def test_can_extract_from_rdf_resource(self):
        node = BNode()
        g = Graph()

        title = faker.sentence()
        url = faker.uri()
        g.add((node, RDF.type, DCAT.Distribution))
        g.add((node, DCT.title, Literal(title)))
        g.add((node, DCAT.downloadURL, Literal(url)))

        resource = resource_from_rdf(g.resource(node))
        resource.validate()

        self.assertIsInstance(resource, Resource)
        self.assertEqual(resource.title, title)
        self.assertEqual(resource.url, url)

    def test_dataset_has_resources(self):
        node = BNode()
        g = Graph()

        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(faker.sentence())))
        for i in range(3):
            rnode = BNode()
            g.set((rnode, RDF.type, DCAT.Distribution))
            g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
            g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(len(dataset.resources), 3)

    def test_dataset_has_resources_from_buggy_plural_distribution(self):
        '''Try to extract resources from the wrong distributions attribute'''
        node = BNode()
        g = Graph()

        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.add((node, DCAT.distributions, rnode))  # use plural name

        dataset = dataset_from_rdf(g)
        dataset.validate()

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(len(dataset.resources), 1)

    def test_dataset_has_resources_from_literal_instead_of_uriref(self):
        node = BNode()
        g = Graph()

        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        # Resource URL is expressed as a Literal
        g.set((rnode, DCAT.downloadURL, Literal(faker.uri())))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        self.assertIsInstance(dataset, Dataset)
        self.assertEqual(len(dataset.resources), 1)

    def test_match_license_from_license_uri(self):
        license = LicenseFactory()
        node = BNode()
        g = Graph()

        g.set((node, RDF.type, DCAT.Dataset))
        g.set((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.set((rnode, DCT.license, URIRef(license.url)))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        self.assertIsInstance(dataset.license, License)
        self.assertEqual(dataset.license, license)

    def test_match_license_from_rights_uri(self):
        license = LicenseFactory()
        node = BNode()
        g = Graph()

        g.set((node, RDF.type, DCAT.Dataset))
        g.set((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.set((rnode, DCT.rights, URIRef(license.url)))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)

        self.assertIsInstance(dataset.license, License)
        self.assertEqual(dataset.license, license)

    def test_match_license_from_license_uri_literal(self):
        license = LicenseFactory()
        node = BNode()
        g = Graph()

        g.set((node, RDF.type, DCAT.Dataset))
        g.set((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.set((rnode, DCT.license, Literal(license.url)))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        self.assertIsInstance(dataset.license, License)
        self.assertEqual(dataset.license, license)

    def test_match_license_from_license_title(self):
        license = LicenseFactory()
        node = BNode()
        g = Graph()

        g.set((node, RDF.type, DCAT.Dataset))
        g.set((node, DCT.title, Literal(faker.sentence())))
        rnode = BNode()
        g.set((rnode, RDF.type, DCAT.Distribution))
        g.set((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.set((rnode, DCT.license, Literal(license.title)))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()

        self.assertIsInstance(dataset.license, License)
        self.assertEqual(dataset.license, license)

    def test_parse_temporal_as_schema_format(self):
        node = BNode()
        g = Graph()
        start = faker.past_date(start_date='-30d')
        end = faker.future_date(end_date='+30d')

        g.set((node, RDF.type, DCT.PeriodOfTime))
        g.set((node, SCHEMA.startDate, Literal(start)))
        g.set((node, SCHEMA.endDate, Literal(end)))

        daterange = temporal_from_rdf(g.resource(node))

        self.assertIsInstance(daterange, db.DateRange)
        self.assertEqual(daterange.start, start)
        self.assertEqual(daterange.end, end)

    def test_parse_temporal_as_iso_interval(self):
        start = faker.past_date(start_date='-30d')
        end = faker.future_date(end_date='+30d')

        pot = Literal('{0}/{1}'.format(start.isoformat(), end.isoformat()))

        daterange = temporal_from_rdf(pot)

        self.assertIsInstance(daterange, db.DateRange)
        self.assertEqual(daterange.start, start)
        self.assertEqual(daterange.end, end)

    def test_parse_temporal_as_iso_year(self):
        pot = Literal('2017')

        daterange = temporal_from_rdf(pot)

        self.assertIsInstance(daterange, db.DateRange)
        self.assertEqual(daterange.start, date(2017, 1, 1))
        self.assertEqual(daterange.end, date(2017, 12, 31))

    def test_parse_temporal_as_iso_month(self):
        pot = Literal('2017-06')

        daterange = temporal_from_rdf(pot)

        self.assertIsInstance(daterange, db.DateRange)
        self.assertEqual(daterange.start, date(2017, 6, 1))
        self.assertEqual(daterange.end, date(2017, 6, 30))

    def test_parse_temporal_as_gov_uk_format(self):
        node = URIRef('http://reference.data.gov.uk/id/year/2017')
        g = Graph()

        g.set((node, RDF.type, DCT.PeriodOfTime))

        daterange = temporal_from_rdf(g.resource(node))

        self.assertIsInstance(daterange, db.DateRange)
        self.assertEqual(daterange.start, date(2017, 1, 1))
        self.assertEqual(daterange.end, date(2017, 12, 31))

    def test_parse_temporal_is_failsafe(self):
        node = URIRef('http://nowhere.org')
        g = Graph()

        g.set((node, RDF.type, DCT.PeriodOfTime))

        self.assertIsNone(temporal_from_rdf(g.resource(node)))
        self.assertIsNone(temporal_from_rdf(Literal('unparseable')))

    def test_unicode(self):
        g = Graph()
        title = 'ééé'
        description = 'éééé'

        node = BNode()
        g.add((node, RDF.type, DCAT.Dataset))
        g.add((node, DCT.title, Literal(title)))
        g.add((node, DCT.description, Literal(description)))

        rnode = BNode()
        g.add((rnode, RDF.type, DCAT.Distribution))
        g.add((rnode, DCT.title, Literal(title)))
        g.add((rnode, DCT.description, Literal(description)))
        g.add((rnode, DCAT.downloadURL, URIRef(faker.uri())))
        g.add((node, DCAT.distribution, rnode))

        dataset = dataset_from_rdf(g)
        dataset.validate()
        self.assertEqual(dataset.title, title)
        self.assertEqual(dataset.description, description)

        resource = dataset.resources[0]
        self.assertEqual(resource.title, title)
        self.assertEqual(resource.description, description)


class DatasetRdfViewsTest(FrontTestCase):
    modules = ['core.dataset', 'core.organization', 'core.user', 'core.site']

    def test_rdf_default_to_jsonld(self):
        dataset = DatasetFactory()
        expected = url_for('datasets.rdf_format',
                           dataset=dataset.id, format='json')
        response = self.get(url_for('datasets.rdf', dataset=dataset))
        self.assertRedirects(response, expected)

    def test_rdf_perform_content_negociation(self):
        dataset = DatasetFactory()
        expected = url_for('datasets.rdf_format',
                           dataset=dataset.id, format='xml')
        url = url_for('datasets.rdf', dataset=dataset)
        headers = {'accept': 'application/xml'}
        response = self.get(url, headers=headers)
        self.assertRedirects(response, expected)

    def test_dataset_rdf_json_ld(self):
        dataset = DatasetFactory()
        for fmt in 'json', 'jsonld':
            url = url_for('datasets.rdf_format', dataset=dataset, format=fmt)
            response = self.get(url)
            self.assert200(response)
            self.assertEqual(response.content_type, 'application/ld+json')
            context_url = url_for('site.jsonld_context', _external=True)
            self.assertEqual(response.json['@context'], context_url)

    def test_dataset_rdf_n3(self):
        dataset = DatasetFactory()
        url = url_for('datasets.rdf_format', dataset=dataset, format='n3')
        response = self.get(url)
        self.assert200(response)
        self.assertEqual(response.content_type, 'text/n3')

    def test_dataset_rdf_turtle(self):
        dataset = DatasetFactory()
        url = url_for('datasets.rdf_format', dataset=dataset, format='ttl')
        response = self.get(url)
        self.assert200(response)
        self.assertEqual(response.content_type, 'application/x-turtle')

    def test_dataset_rdf_rdfxml(self):
        dataset = DatasetFactory()
        for fmt in 'xml', 'rdf', 'rdfs', 'owl':
            url = url_for('datasets.rdf_format', dataset=dataset, format=fmt)
            response = self.get(url)
            self.assert200(response)
            self.assertEqual(response.content_type, 'application/rdf+xml')

    def test_dataset_rdf_n_triples(self):
        dataset = DatasetFactory()
        url = url_for('datasets.rdf_format', dataset=dataset, format='nt')
        response = self.get(url)
        self.assert200(response)
        self.assertEqual(response.content_type, 'application/n-triples')

    def test_dataset_rdf_trig(self):
        dataset = DatasetFactory()
        url = url_for('datasets.rdf_format', dataset=dataset, format='trig')
        response = self.get(url)
        self.assert200(response)
        self.assertEqual(response.content_type, 'application/trig')
