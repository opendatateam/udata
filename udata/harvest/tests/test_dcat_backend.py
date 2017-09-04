# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os

import httpretty

from datetime import date

from udata.models import Dataset, License
from udata.tests import TestCase, DBTestMixin
from udata.core.organization.factories import OrganizationFactory

from .factories import HarvestSourceFactory
from .. import actions

log = logging.getLogger(__name__)


TEST_DOMAIN = 'data.test.org'  # Need to be used in fixture file
DCAT_URL_PATTERN = 'http://{domain}/{path}'
DCAT_FILES_DIR = os.path.join(os.path.dirname(__file__), 'dcat')


def mock_dcat(filename):
    url = DCAT_URL_PATTERN.format(path=filename, domain=TEST_DOMAIN)
    with open(os.path.join(DCAT_FILES_DIR, filename)) as dcatfile:
        body = dcatfile.read()
    httpretty.register_uri(httpretty.GET, url, body=body)
    return url


def mock_pagination(path, pattern):
    url = DCAT_URL_PATTERN.format(path=path, domain=TEST_DOMAIN)

    def callback(request, uri, headers):
        page = request.querystring.get('page', [1])[0]
        filename = pattern.format(page=page)
        with open(os.path.join(DCAT_FILES_DIR, filename)) as dcatfile:
            return 200, {}, dcatfile.read()

    httpretty.register_uri(httpretty.GET, url, body=callback)
    return url


class DcatBackendTest(DBTestMixin, TestCase):
    def setUp(self):
        super(DcatBackendTest, self).setUp()
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

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        self.assertEqual(len(job.items), 3)

        datasets = {d.extras['dct:identifier']: d for d in Dataset.objects}

        self.assertEqual(len(datasets), 3)

        for i in '1 2 3'.split():
            d = datasets[i]
            self.assertEqual(d.title, 'Dataset {0}'.format(i))
            self.assertEqual(d.description,
                             'Dataset {0} description'.format(i))
            self.assertEqual(d.extras['dct:identifier'], i)

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

    @httpretty.activate
    def test_simple_nested_attributes(self):
        filename = 'nested.jsonld'
        url = mock_dcat(filename)
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=OrganizationFactory())

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        self.assertEqual(len(job.items), 1)

        dataset = Dataset.objects.first()
        self.assertIsNotNone(dataset.temporal_coverage)
        self.assertEqual(dataset.temporal_coverage.start, date(2016, 1, 1))
        self.assertEqual(dataset.temporal_coverage.end, date(2016, 12, 5))

        self.assertEqual(len(dataset.resources), 1)

        resource = dataset.resources[0]
        self.assertIsNotNone(resource.checksum)
        self.assertEqual(resource.checksum.type, 'sha1')
        self.assertEqual(resource.checksum.value,
                         'fb4106aa286a53be44ec99515f0f0421d4d7ad7d')

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

        datasets = {d.extras['dct:identifier']: d for d in Dataset.objects}

        self.assertEqual(len(datasets), 3)
        self.assertEqual(len(datasets['1'].resources), 2)
        self.assertEqual(len(datasets['2'].resources), 2)
        self.assertEqual(len(datasets['3'].resources), 1)

    @httpretty.activate
    def test_hydra_partial_collection_view_pagination(self):
        url = mock_pagination('catalog.jsonld',
                              'partial-collection-{page}.jsonld')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        self.assertEqual(len(job.items), 4)

    @httpretty.activate
    def test_hydra_legacy_paged_collection_pagination(self):
        url = mock_pagination('catalog.jsonld',
                              'paged-collection-{page}.jsonld')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        self.assertEqual(len(job.items), 4)

    @httpretty.activate
    def test_failure_on_initialize(self):
        url = DCAT_URL_PATTERN.format(path='', domain=TEST_DOMAIN)
        httpretty.register_uri(httpretty.GET, url, body='should fail')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        self.assertEqual(job.status, 'failed')

    @httpretty.activate
    def test_unsupported_mime_type(self):
        url = DCAT_URL_PATTERN.format(path='', domain=TEST_DOMAIN)
        httpretty.register_uri(httpretty.HEAD, url, content_type='text/html; charset=utf-8')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        self.assertEqual(job.status, 'failed')
        self.assertEqual(len(job.errors), 1)

        error = job.errors[0]
        self.assertEqual(error.message, 'Unsupported mime type "text/html"')

    @httpretty.activate
    def test_unable_to_detect_format(self):
        url = DCAT_URL_PATTERN.format(path='', domain=TEST_DOMAIN)
        httpretty.register_uri(httpretty.HEAD, url, content_type='')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        self.assertEqual(job.status, 'failed')
        self.assertEqual(len(job.errors), 1)

        error = job.errors[0]
        expected = 'Unable to detect format from extension or mime type'
        self.assertEqual(error.message, expected)
