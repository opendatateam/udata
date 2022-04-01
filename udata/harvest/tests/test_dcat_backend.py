import logging
import os

import pytest

from datetime import date

from udata.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.dataset.factories import LicenseFactory

from .factories import HarvestSourceFactory
from .. import actions

log = logging.getLogger(__name__)


TEST_DOMAIN = 'data.test.org'  # Need to be used in fixture file
DCAT_URL_PATTERN = 'http://{domain}/{path}'
DCAT_FILES_DIR = os.path.join(os.path.dirname(__file__), 'dcat')


def mock_dcat(rmock, filename, path=None):
    url = DCAT_URL_PATTERN.format(path=path or filename, domain=TEST_DOMAIN)
    with open(os.path.join(DCAT_FILES_DIR, filename)) as dcatfile:
        body = dcatfile.read()
    rmock.get(url, text=body)
    return url


def mock_pagination(rmock, path, pattern):
    url = DCAT_URL_PATTERN.format(path=path, domain=TEST_DOMAIN)

    def callback(request, context):
        page = request.qs.get('page', [1])[0]
        filename = pattern.format(page=page)
        context.status_code = 200
        with open(os.path.join(DCAT_FILES_DIR, filename)) as dcatfile:
            return dcatfile.read()

    rmock.get(rmock.ANY, text=callback)
    return url


@pytest.mark.usefixtures('clean_db')
@pytest.mark.options(PLUGINS=['dcat'])
class DcatBackendTest:

    def test_simple_flat(self, rmock):
        filename = 'flat.jsonld'
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 3

        datasets = {d.extras['dct:identifier']: d for d in Dataset.objects}

        assert len(datasets) == 3

        for i in '1 2 3'.split():
            d = datasets[i]
            assert d.title == 'Dataset {0}'.format(i)
            assert d.description == 'Dataset {0} description'.format(i)
            assert d.extras['dct:identifier'] == i

        # First dataset
        dataset = datasets['1']
        assert dataset.tags == ['tag-1', 'tag-2', 'tag-3', 'tag-4',
                                'theme-1', 'theme-2']
        assert len(dataset.resources) == 2

        # Second dataset
        dataset = datasets['2']
        assert dataset.tags == ['tag-1', 'tag-2', 'tag-3']
        assert len(dataset.resources) == 2

        # Third dataset
        dataset = datasets['3']
        assert dataset.tags == ['tag-1', 'tag-2']
        assert len(dataset.resources) == 1

    def test_flat_with_blank_nodes(self, rmock):
        filename = 'bnodes.jsonld'
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        datasets = {d.extras['dct:identifier']: d for d in Dataset.objects}

        assert len(datasets) == 3
        assert len(datasets['1'].resources) == 2
        assert len(datasets['2'].resources) == 2
        assert len(datasets['3'].resources) == 1

    def test_simple_nested_attributes(self, rmock):
        filename = 'nested.jsonld'
        url = mock_dcat(rmock, filename)
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=OrganizationFactory())

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 1

        dataset = Dataset.objects.first()
        assert dataset.temporal_coverage is not None
        assert dataset.temporal_coverage.start == date(2016, 1, 1)
        assert dataset.temporal_coverage.end == date(2016, 12, 5)
        assert dataset.extras['remote_url'] == 'http://data.test.org/datasets/1'

        assert len(dataset.resources) == 1

        resource = dataset.resources[0]
        assert resource.checksum is not None
        assert resource.checksum.type == 'sha1'
        assert (resource.checksum.value
                == 'fb4106aa286a53be44ec99515f0f0421d4d7ad7d')

    def test_idempotence(self, rmock):
        filename = 'flat.jsonld'
        url = mock_dcat(rmock, filename)
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        # Run the same havester twice
        actions.run(source.slug)
        actions.run(source.slug)

        datasets = {d.extras['dct:identifier']: d for d in Dataset.objects}

        assert len(datasets) == 3
        assert len(datasets['1'].resources) == 2
        assert len(datasets['2'].resources) == 2
        assert len(datasets['3'].resources) == 1

    def test_hydra_partial_collection_view_pagination(self, rmock):
        url = mock_pagination(rmock, 'catalog.jsonld',
                              'partial-collection-{page}.jsonld')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 4

    def test_hydra_legacy_paged_collection_pagination(self, rmock):
        url = mock_pagination(rmock, 'catalog.jsonld',
                              'paged-collection-{page}.jsonld')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()
        assert len(job.items) == 4

    def test_failure_on_initialize(self, rmock):
        url = DCAT_URL_PATTERN.format(path='', domain=TEST_DOMAIN)
        rmock.get(url, text='should fail')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        assert job.status == 'failed'

    def test_supported_mime_type(self, rmock):
        url = mock_dcat(rmock, 'catalog.xml', path='without/extension')
        rmock.head(url, headers={'Content-Type': 'application/xml; charset=utf-8'})
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        assert job.status == 'done'
        assert job.errors == []
        assert len(job.items) == 3

    def test_xml_catalog(self, rmock):
        LicenseFactory(id='lov2', title='Licence Ouverte Version 2.0')

        url = mock_dcat(rmock, 'catalog.xml', path='catalog.xml')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        # test dct:license support
        extras = {'extras__dct:identifier': '3'}
        dataset = Dataset.objects.get(**extras)
        assert dataset.license.id == 'lov2'
        assert dataset.extras['remote_url'] == 'http://data.test.org/datasets/3'
        assert dataset.created_at.date() == date(2016, 12, 14)
        assert dataset.last_modified.date() == date(2016, 12, 14)
        assert dataset.frequency == 'daily'
        assert dataset.description == 'Dataset 3 description'

        extras = {'extras__dct:identifier': '1'}
        dataset = Dataset.objects.get(**extras)
        # test abstract description support
        assert dataset.description == 'Dataset 1 description'

    def test_geonetwork_xml_catalog(self, rmock):
        url = mock_dcat(rmock, 'geonetwork.xml', path='catalog.xml')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)
        actions.run(source.slug)
        dataset = Dataset.objects.filter(organization=org).first()
        assert dataset is not None
        assert dataset.created_at.date() == date(2004, 11, 3)
        assert dataset.description.startswith('Data of type chemistry')

    def test_sigoreme_xml_catalog(self, rmock):
        LicenseFactory(id='fr-lo', title='Licence ouverte / Open Licence')
        url = mock_dcat(rmock, 'sig.oreme.rdf')
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)
        actions.run(source.slug)
        dataset = Dataset.objects.filter(organization=org).first()

        assert dataset is not None
        assert dataset.frequency == 'irregular'
        assert 'gravi' in dataset.tags  # support dcat:keyword
        assert 'geodesy' in dataset.tags  # support dcat:theme
        assert dataset.license.id == 'fr-lo'
        assert len(dataset.resources) == 1
        assert dataset.description.startswith('Data from the \'National network')

    def test_unsupported_mime_type(self, rmock):
        url = DCAT_URL_PATTERN.format(path='', domain=TEST_DOMAIN)
        rmock.head(url, headers={'Content-Type': 'text/html; charset=utf-8'})
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        assert job.status == 'failed'
        assert len(job.errors) == 1

        error = job.errors[0]
        assert error.message == 'Unsupported mime type "text/html"'

    def test_unable_to_detect_format(self, rmock):
        url = DCAT_URL_PATTERN.format(path='', domain=TEST_DOMAIN)
        rmock.head(url, headers={'Content-Type': ''})
        org = OrganizationFactory()
        source = HarvestSourceFactory(backend='dcat',
                                      url=url,
                                      organization=org)

        actions.run(source.slug)

        source.reload()

        job = source.get_last_job()

        assert job.status == 'failed'
        assert len(job.errors) == 1

        error = job.errors[0]
        expected = 'Unable to detect format from extension or mime type'
        assert error.message == expected
