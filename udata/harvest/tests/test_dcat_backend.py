# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
import os

from datetime import datetime
from uuid import uuid4

import httpretty

from udata.models import Dataset, License
from udata.tests import TestCase, DBTestMixin
from udata.core.organization.factories import OrganizationFactory
from udata.utils import faker

from .factories import HarvestSourceFactory
from .. import actions

log = logging.getLogger(__name__)


DCAT_URL = 'http://data.test.org/dcat.json'
DCAT_URL_PATTERN = 'http://data.test.org/{filename}'
DCAT_FILES_DIR = os.path.join(os.path.dirname(__file__), 'dcat')

TEST_FORMATS = {
    'html': 'text/html',
    'json': 'application/json',
    'GeoJSON': 'application/vnd.geo+json',
    'CSV': 'text/csv',
    'KML': 'application/vnd.google-earth.kml+xml',
    'ZIP': "application/zip",
}


def html_factory():
    return '<div>{0}</div>'.format(faker.paragraph())


def dcat_distribution_factory(fileformat, mimetype):
    return {
        "@type": "dcat:Distribution",
        "title": faker.sentence(),
        "format": fileformat,
        "mediaType": mimetype,
        "accessURL": faker.uri()
    }


def dcat_dataset_factory(**kwargs):
    created = faker.date_time_between(start_date='-3y', end_date='-7d')
    updated = faker.date_time_between(start_date='-7d', end_date='now')
    # nb_resources = faker.randomize_nb_elements(4)
    nb_tags = faker.randomize_nb_elements(10)
    url = faker.uri()
    data = {
        "@type": "dcat:Dataset",
        "identifier": url,
        "title": faker.sentence(),
        "description": html_factory(),
        "keyword": [
            faker.word() for _ in range(nb_tags)
        ],
        "issued": created.isoformat(),
        "modified": updated.isoformat(),
        "publisher": {
            "name": "Atelier Parisien d'Urbanisme"
        },
        "contactPoint": {
            "@type": "vcard:Contact",
            "fn": "Emmanuel FAURE",
            "hasEmail": "mailto:"
        },
        "accessLevel": "public",
        "distribution": [
            dcat_distribution_factory(fmt, mime)
            for fmt, mime in TEST_FORMATS.items()
        ],
        "landingPage": faker.uri(),
        "webService": faker.uri(),
        "license": faker.uri(),
        "spatial": "2.2052,48.7577,2.4371,48.9599",
        "theme": [faker.word()]
    }
    data.update(kwargs)
    return data


def dcat_catalog_factory(*datasets):
    return {
        "@context": "https://project-open-data.cio.gov/v1.1/schema/catalog.jsonld",
        "@type": "dcat:Catalog",
        "conformsTo": "https://project-open-data.cio.gov/v1.1/schema",
        "describedBy": "https://project-open-data.cio.gov/v1.1/schema/catalog.json",
        "datasets": [datasets],
    }


def mock_dcat(filename):
    url = DCAT_URL_PATTERN.format(filename=filename)
    with open(os.path.join(DCAT_FILES_DIR, filename)) as dcatfile:
        body = dcatfile.read()
    httpretty.register_uri(httpretty.GET, url, body=body)
    #    content_type='application/json')
    return url


class DcatBackendTest(DBTestMixin, TestCase):
    def setUp(self):
        # Create fake licenses
        for license_id in 'lool', 'fr-lo':
            License.objects.create(id=license_id, title=license_id)

    @httpretty.activate
    def test_simple_flat(self):
        filename = 'flat.jsonld'
        url = mock_dcat(filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        # data = [
        #     dcat_dataset_factory(),
        #     dcat_dataset_factory(),
        #     dcat_dataset_factory(),
        # ]

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        self.assertEqual(len(job.items), 3)

        datasets = {d.extras['dcat:identifier']: d for d in Dataset.objects}

        self.assertEqual(len(datasets), 3)

        for i in '1 2 3'.split():
            d = datasets[i]
            self.assertEqual(d.title, 'Dataset {0}'.format(i))
            self.assertEqual(d.description,
                             'Dataset {0} description'.format(i))
            self.assertEqual(d.extras['dcat:identifier'], i)

        # First dataset
        dataset = datasets['1']
        self.assertEqual(dataset.tags, ['tag-1', 'tag-2', 'tag-3', 'tag-4',
                                        'theme-1', 'theme-2'])
        self.assertEqual(len(dataset.resources), 2)

        # Second dataset
        dataset = datasets['2']
        self.assertEqual(dataset.tags, ['tag-1', 'tag-2', 'tag-3'])
        self.assertEqual(len(dataset.resources), 2)

        # Third dataset
        dataset = datasets['3']
        self.assertEqual(dataset.tags, ['tag-1', 'tag-2'])
        self.assertEqual(len(dataset.resources), 1)

        # for dcat in data:
        #     self.assertIn(dcat['identifier'], datasets)
        #     d = datasets[dcat['identifier']]

        # self.assertIn('dataset-1', datasets)
        # d = datasets['dataset-1']
        # self.assertEqual(d.title, 'Dataset 1')
        # self.assertEqual(d.description, "Description 1")
        # self.assertEqual(d.tags, ['country-uk',
        #                           'date-2009',
        #                           'openspending',
        #                           'regional'])
        # self.assertEqual(d.extras['harvest:remote_id'],
        #                  '7e4d4ef3-f452-4c35-963d-9c6e582374b3')
        # self.assertEqual(d.extras['harvest:domain'], 'ckan.test.org')
        # self.assertEqual(d.extras['ckan:name'], 'dataset-1')
        # # self.assertEqual(d.license.id, "fr-lo")
        #
        # self.assertEqual(len(d.resources), 3)
        # resource = d.resources[0]
        # self.assertEqual(resource.title, 'Resource 1')
        # self.assertEqual(resource.description, 'Resource description 1')
        # self.assertEqual(resource.format, 'csv')
        # self.assertEqual(resource.mime, 'text/csv')
        # self.assertIsInstance(resource.modified, datetime)
        # self.assertEqual(resource.url,
        #                  ('http://ckan.net/storage/f/file/'
        #                   '3ffdcd42-5c63-4089-84dd-c23876259973'))
        #
        # # dataset-2 has geo feature
        # self.assertIn('dataset-2', datasets)
        # d = datasets['dataset-2']
        # self.assertEqual(d.tags, ['africa',
        #                           'bandwidth',
        #                           'broadband',
        #                           'cables',
        #                           'fibre',
        #                           'optic',
        #                           'terrestrial'])
        # self.assertEqual(len(d.resources), 1)
        # self.assertEqual(d.spatial.geom['coordinates'],
        #                  [[[[50.8, -34.2],
        #                     [50.8, 36.7],
        #                     [-19.9, 36.7],
        #                     [-19.9, -34.2],
        #                     [50.8, -34.2]]]])
        #
        # # dataset-3 has no data
        # self.assertNotIn('dataset-3', datasets)

    @httpretty.activate
    def test_idempotence(self):
        filename = 'flat.jsonld'
        url = mock_dcat(filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        # Run the same havester twice
        actions.run(source.slug)
        actions.run(source.slug)

        datasets = {d.extras['dcat:identifier']: d for d in Dataset.objects}

        self.assertEqual(len(datasets), 3)
        self.assertEqual(len(datasets['1'].resources), 2)
        self.assertEqual(len(datasets['2'].resources), 2)
        self.assertEqual(len(datasets['3'].resources), 1)
