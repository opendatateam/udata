# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import cgi
import json

import pytest
import requests

from flask import url_for
from werkzeug.contrib.atom import AtomFeed

from udata.core.dataset.factories import (
    DatasetFactory, LicenseFactory, VisibleDatasetFactory
)
from udata.core.reuse.factories import ReuseFactory, VisibleReuseFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.factories import SpatialCoverageFactory
from udata.frontend.markdown import md
from udata.models import Badge, PUBLIC_SERVICE
from udata.settings import Testing
from udata.tests.features.territories.test_territories_process import (
    create_geozones_fixtures
)
from udata.utils import faker
from udata.tests.helpers import assert200, assert404, assert_redirects

from .models import (
    DATACONNEXIONS_5_CANDIDATE, DATACONNEXIONS_6_CANDIDATE,
    TERRITORY_DATASETS, OPENFIELD16, SPD
)
from .views import DATACONNEXIONS_5_CATEGORIES, DATACONNEXIONS_6_CATEGORIES
from .metrics import PublicServicesMetric


class GouvFrSettings(Testing):
    TEST_WITH_THEME = True
    TEST_WITH_PLUGINS = True
    PLUGINS = ['gouvfr']
    THEME = 'gouvfr'
    WP_ATOM_URL = None  # Only activated on specific tests
    DISCOURSE_URL = None  # Only activated on specific tests


class GouvFrThemeTest:
    '''Ensure themed views render'''
    settings = GouvFrSettings
    modules = []

    def test_render_home(self, autoindex, client):
        '''It should render the home page'''
        with autoindex:
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organization=org)
                ReuseFactory(organization=org)

        response = client.get(url_for('site.home'))
        assert200(response)

    def test_render_home_no_data(self, client):
        '''It should render the home page without data'''
        response = client.get(url_for('site.home'))
        assert200(response)

    def test_render_search(self, autoindex, client):
        '''It should render the search page'''
        with autoindex:
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organization=org)
                ReuseFactory(organization=org)

        response = client.get(url_for('search.index'))
        assert200(response)

    def test_render_search_no_data(self, autoindex, client):
        '''It should render the search page without data'''
        response = client.get(url_for('search.index'))
        assert200(response)

    def test_render_metrics(self, client):
        '''It should render the dashboard page'''
        for i in range(3):
            org = OrganizationFactory()
            DatasetFactory(organization=org)
            ReuseFactory(organization=org)
        response = client.get(url_for('site.dashboard'))
        assert200(response)

    def test_render_metrics_no_data(self, client):
        '''It should render the dashboard page without data'''
        response = client.get(url_for('site.dashboard'))
        assert200(response)

    def test_render_dataset_page(self, client):
        '''It should render the dataset page'''
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        ReuseFactory(organization=org, datasets=[dataset])

        response = client.get(url_for('datasets.show', dataset=dataset))
        assert200(response)

    def test_render_organization_page(self, client):
        '''It should render the organization page'''
        org = OrganizationFactory()
        datasets = [DatasetFactory(organization=org) for _ in range(3)]
        for dataset in datasets:
            ReuseFactory(organization=org, datasets=[dataset])

        response = client.get(url_for('organizations.show', org=org))
        assert200(response)

    def test_render_reuse_page(self, client):
        '''It should render the reuse page'''
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        reuse = ReuseFactory(organization=org, datasets=[dataset])

        response = client.get(url_for('reuses.show', reuse=reuse))
        assert200(response)


WP_ATOM_URL = 'http://somewhere.test/feed.atom'


@pytest.mark.options(WP_ATOM_URL=WP_ATOM_URL)
class GouvFrHomeBlogTest:
    '''Ensure home page render with blog'''
    settings = GouvFrSettings
    modules = []

    def test_render_home_with_blog(self, rmock, client):
        '''It should render the home page with the latest blog article'''
        post_url = faker.uri()
        feed = AtomFeed('Some blog', feed_url=WP_ATOM_URL)
        feed.add('Some post',
                 '<div>Some content</div>',
                 content_type='html',
                 author=faker.name(),
                 url=post_url,
                 updated=faker.date_time(),
                 published=faker.date_time())
        rmock.get(WP_ATOM_URL, text=feed.to_string(),
                  headers={'Content-Type': 'application/atom+xml'})
        response = client.get(url_for('site.home'))
        assert200(response)
        assert 'Some post' in response.data.decode('utf8')
        assert post_url in response.data.decode('utf8')

    def test_render_home_if_blog_timeout(self, rmock, client):
        '''It should render the home page when blog time out'''
        rmock.get(WP_ATOM_URL, exc=requests.Timeout('Blog timed out'))
        response = client.get(url_for('site.home'))
        assert200(response)

    def test_render_home_if_blog_error(self, rmock, client):
        '''It should render the home page when blog is not available'''
        rmock.get(WP_ATOM_URL, exc=requests.ConnectionError('Error'))
        response = client.get(url_for('site.home'))
        assert200(response)


DISCOURSE_URL = 'http://somewhere.test/discourse'


@pytest.mark.options(DISCOURSE_URL=DISCOURSE_URL,
                     DISCOURSE_LISTING_TYPE='latest',
                     DISCOURSE_CATEGORY_ID=None)
class GouvFrHomeDiscourseTest:
    '''Ensure home page render with forum'''
    settings = GouvFrSettings
    modules = []

    def test_render_home_with_discourse(self, rmock, client):
        '''It should render the home page with the latest forum topic'''
        data = {
            'categories': [{
                'id': 1,
                'name': 'Category #1',
            }]
        }
        data_latest = {
            'users': [],
            'topic_list': {
                'topics': [
                    {
                        'last_posted_at': '2017-01-01',
                        'id': 1,
                        'title': 'Title',
                        'fancy_title': 'Fancy Title',
                        'slug': 'title',
                        'category_id': 1,
                        'posts_count': 1,
                        'reply_count': 1,
                        'like_count': 1,
                        'views': 1,
                        'created_at': '2017-01-01',
                        'posters': [],
                    }
                ],
            },
        }
        rmock.get('%s/site.json' % DISCOURSE_URL, json=data)
        rmock.get('%s/l/latest.json' % DISCOURSE_URL, json=data_latest)
        response = client.get(url_for('site.home'))
        assert200(response)
        assert 'Title' in response.data.decode('utf8')

    def test_render_home_if_discourse_timeout(self, rmock, client):
        '''It should render the home page when forum time out'''
        url = '%s/site.json' % DISCOURSE_URL
        rmock.get(url, exc=requests.Timeout('Blog timed out'))
        response = client.get(url_for('site.home'))
        assert200(response)

    def test_render_home_if_discourse_error(self, rmock, client):
        '''It should render the home page when forum is not available'''
        url = '%s/site.json' % DISCOURSE_URL
        rmock.get(url, exc=requests.ConnectionError('Error'))
        response = client.get(url_for('site.home'))
        assert200(response)


@pytest.mark.usefixtures('clean_db')
class GouvFrMetricsTest:
    '''Check metrics'''
    settings = GouvFrSettings

    def test_public_services(self):
        ps_badge = Badge(kind=PUBLIC_SERVICE)
        public_services = [
            OrganizationFactory(badges=[ps_badge]) for _ in range(2)
        ]
        for _ in range(3):
            OrganizationFactory()

        assert PublicServicesMetric().get_value() == len(public_services)


@pytest.mark.options(DEFAULT_LANGUAGE='en')
class LegacyUrlsTest:
    settings = GouvFrSettings
    modules = []

    def test_redirect_datasets(self, client):
        dataset = DatasetFactory()
        response = client.get('/en/dataset/%s/' % dataset.slug)
        assert_redirects(response, url_for('datasets.show', dataset=dataset))

    def test_redirect_datasets_not_found(self, client):
        response = client.get('/en/DataSet/wtf')
        assert404(response)

    def test_redirect_organizations(self, client):
        org = OrganizationFactory()
        response = client.get('/en/organization/%s/' % org.slug)
        assert_redirects(response, url_for('organizations.show', org=org))

    def test_redirect_organization_list(self, client):
        response = client.get('/en/organization/')
        assert_redirects(response, url_for('organizations.list'))

    def test_redirect_topics(self, client):
        response = client.get('/en/group/societe/')
        assert_redirects(response, url_for('topics.display', topic='societe'))


class SpecificUrlsTest:
    settings = GouvFrSettings
    modules = []

    def test_redevances(self, client):
        response = client.get(url_for('gouvfr.redevances'))
        assert200(response)

    def test_terms(self, client):
        response = client.get(url_for('site.terms'))
        assert200(response)

    def test_licences(self, client):
        response = client.get(url_for('gouvfr.licences'))
        assert200(response)


class DataconnexionsTest:
    settings = GouvFrSettings
    modules = []

    def test_redirect_to_last_dataconnexions(self, client):
        response = client.get(url_for('gouvfr.dataconnexions'))
        assert_redirects(response, url_for('gouvfr.dataconnexions6'))

    def test_render_dataconnexions_5_without_data(self, client):
        response = client.get(url_for('gouvfr.dataconnexions5'))
        assert200(response)

    def test_render_dataconnexions_5_with_data(self, client):
        for tag, label, description in DATACONNEXIONS_5_CATEGORIES:
            badge = Badge(kind=DATACONNEXIONS_5_CANDIDATE)
            VisibleReuseFactory(tags=[tag], badges=[badge])
        response = client.get(url_for('gouvfr.dataconnexions5'))
        assert200(response)

    def test_render_dataconnexions_6_without_data(self, client):
        response = client.get(url_for('gouvfr.dataconnexions6'))
        assert200(response)

    def test_render_dataconnexions_6_with_data(self, client):
        # Use tags until we are sure all reuse are correctly labeled
        for tag, label, description in DATACONNEXIONS_6_CATEGORIES:
            badge = Badge(kind=DATACONNEXIONS_6_CANDIDATE)
            VisibleReuseFactory(tags=['dataconnexions-6', tag], badges=[badge])
        response = client.get(url_for('gouvfr.dataconnexions6'))
        assert200(response)


class C3Test:
    settings = GouvFrSettings
    modules = []

    def test_redirect_c3(self, client):
        response = client.get(url_for('gouvfr.c3'))
        assert_redirects(response, '/en/climate-change-challenge')

    def test_render_c3_without_data(self, client):
        response = client.get(url_for('gouvfr.climate_change_challenge'))
        assert200(response)


class OpenField16Test:
    settings = GouvFrSettings
    modules = []

    def test_render_without_data(self, client):
        response = client.get(url_for('gouvfr.openfield16'))
        assert200(response)

    def test_render_with_data(self, client):
        for i in range(3):
            badge = Badge(kind=OPENFIELD16)
            VisibleDatasetFactory(badges=[badge])
        response = client.get(url_for('gouvfr.openfield16'))
        assert200(response)


class SpdTest:
    settings = GouvFrSettings
    modules = []

    def test_render_without_data(self, client):
        response = client.get(url_for('gouvfr.spd'))
        assert200(response)

    def test_render_with_data(self, client):
        for i in range(3):
            badge = Badge(kind=SPD)
            VisibleDatasetFactory(badges=[badge])
        response = client.get(url_for('gouvfr.spd'))
        assert200(response)


class TerritoriesSettings(GouvFrSettings):
    ACTIVATE_TERRITORIES = True
    HANDLED_LEVELS = ('fr:commune', 'fr:departement', 'fr:region')


class TerritoriesTest:
    settings = TerritoriesSettings
    modules = []

    def test_with_gouvfr_town_territory_datasets(self, client, templates):
        paca, bdr, arles = create_geozones_fixtures()
        url = url_for('territories.territory', territory=arles)
        with templates.capture():
            response = client.get(url)
        assert200(response)
        data = response.data.decode('utf-8')
        assert arles.name in data
        base_datasets = templates.get_context_variable('base_datasets')
        assert len(base_datasets) == 9
        expected = '<div data-udata-territory-id="{dataset.slug}"'
        for dataset in base_datasets:
            assert expected.format(dataset=dataset) in data
        assert bdr.name in data

    def test_with_gouvfr_county_territory_datasets(self, client, templates):
        paca, bdr, arles = create_geozones_fixtures()
        url = url_for('territories.territory', territory=bdr)
        with templates.capture():
            response = client.get(url)
        assert200(response)
        data = response.data.decode('utf-8')
        assert bdr.name in data
        base_datasets = templates.get_context_variable('base_datasets')
        assert len(base_datasets) == 7
        expected = '<div data-udata-territory-id="{dataset.slug}"'
        for dataset in base_datasets:
            assert expected.format(dataset=dataset) in data

    def test_with_gouvfr_region_territory_datasets(self, client, templates):
        paca, bdr, arles = create_geozones_fixtures()
        url = url_for('territories.territory', territory=paca)
        with templates.capture():
            response = client.get(url)
        assert200(response)
        data = response.data.decode('utf-8')
        assert paca.name in data
        base_datasets = templates.get_context_variable('base_datasets')
        assert len(base_datasets) == 7
        expected = '<div data-udata-territory-id="{dataset.slug}"'
        for dataset in base_datasets:
            assert expected.format(dataset=dataset) in data


class OEmbedsTerritoryAPITest:
    settings = TerritoriesSettings
    modules = []

    def test_oembed_town_territory_api_get(self, api):
        '''It should fetch a town territory in the oembed format.'''
        paca, bdr, arles = create_geozones_fixtures()
        licence_ouverte = LicenseFactory(id='fr-lo', title='Licence Ouverte')
        odbl_license = LicenseFactory(id='odc-odbl', title='ODbL')
        LicenseFactory(id='notspecified', title='Not Specified')
        town_datasets = TERRITORY_DATASETS['commune']
        for territory_dataset_class in town_datasets.values():
            organization = OrganizationFactory(
                id=territory_dataset_class.organization_id)
            territory = territory_dataset_class(arles)
            reference = 'territory-{id}'.format(id=territory.slug)
            response = api.get(url_for('api.oembeds', references=reference))
            assert200(response)
            data = json.loads(response.data)[0]
            assert 'html' in data
            assert 'width' in data
            assert 'maxwidth' in data
            assert 'height' in data
            assert 'maxheight' in data
            assert data['type'] == 'rich'
            assert data['version'] == '1.0'

            html = data['html']
            assert territory.title in html
            assert cgi.escape(territory.url) in html
            assert 'alt="{name}"'.format(name=organization.name) in html
            assert md(territory.description, source_tooltip=True) in html
            assert 'Download from local.test' in html
            assert 'Add to your own website' in html
            if territory_dataset_class not in (town_datasets['comptes_com'],):
                if territory_dataset_class == town_datasets['ban_odbl_com']:
                    license = odbl_license
                else:
                    license = licence_ouverte
                assert 'License: {title}'.format(title=license.title) in html
                assert '© {license_id}'.format(license_id=license.id) in html
                assert (
                    '<a data-tooltip="Source" href="http://local.test/datasets'
                    in html)

    def test_oembed_county_territory_api_get(self, api):
        '''It should fetch a county territory in the oembed format.'''
        paca, bdr, arles = create_geozones_fixtures()
        licence_ouverte = LicenseFactory(id='fr-lo', title='Licence Ouverte')
        LicenseFactory(id='notspecified', title='Not Specified')
        for dataset_class in TERRITORY_DATASETS['departement'].values():
            organization = OrganizationFactory(
                id=dataset_class.organization_id)
            territory = dataset_class(bdr)
            reference = 'territory-{id}'.format(id=territory.slug)
            response = api.get(url_for('api.oembeds', references=reference))
            assert200(response)
            data = json.loads(response.data)[0]
            assert 'html' in data
            assert 'width' in data
            assert 'maxwidth' in data
            assert 'height' in data
            assert 'maxheight' in data
            assert data['type'] == 'rich'
            assert data['version'] == '1.0'

            html = data['html']
            assert territory.title in html
            assert cgi.escape(territory.url) in html
            assert 'alt="{name}"'.format(name=organization.name) in html
            assert md(territory.description, source_tooltip=True) in html
            assert 'Download from local.test' in html
            assert 'Add to your own website' in html
            if dataset_class not in (
                    TERRITORY_DATASETS['departement']['comptes_dep'],
                    TERRITORY_DATASETS['departement']['zonages_dep']):
                assert 'License: {0}'.format(licence_ouverte.title) in html
                assert '© {0}'.format(licence_ouverte.id) in html
                assert (
                    '<a data-tooltip="Source" href="http://local.test/datasets'
                    in html)

    def test_oembed_region_territory_api_get(self, api):
        '''It should fetch a region territory in the oembed format.'''
        paca, bdr, arles = create_geozones_fixtures()
        licence_ouverte = LicenseFactory(id='fr-lo', title='Licence Ouverte')
        LicenseFactory(id='notspecified', title='Not Specified')
        for territory_dataset_class in TERRITORY_DATASETS['region'].values():
            organization = OrganizationFactory(
                id=territory_dataset_class.organization_id)
            territory = territory_dataset_class(paca)
            reference = 'territory-{id}'.format(id=territory.slug)
            response = api.get(url_for('api.oembeds', references=reference))
            assert200(response)
            data = json.loads(response.data)[0]
            assert 'html' in data
            assert 'width' in data
            assert 'maxwidth' in data
            assert 'height' in data
            assert 'maxheight' in data
            assert data['type'] == 'rich'
            assert data['version'] == '1.0'

            html = data['html']
            assert territory.title in html
            assert cgi.escape(territory.url) in html
            assert 'alt="{name}"'.format(name=organization.name) in html
            assert md(territory.description, source_tooltip=True) in html
            assert 'Download from local.test' in html
            assert 'Add to your own website' in html
            if territory_dataset_class not in (
                    TERRITORY_DATASETS['region']['comptes_reg'],
                    TERRITORY_DATASETS['region']['zonages_reg']):
                assert 'License: {0}'.format(licence_ouverte.title) in html
                assert '© {0}'.format(licence_ouverte.id) in html
                assert (
                    '<a data-tooltip="Source" href="http://local.test/datasets'
                    in html)


class SpatialTerritoriesApiTest:
    settings = TerritoriesSettings
    modules = []

    def test_datasets_with_dynamic_region(self, autoindex, client):
        paca, bdr, arles = create_geozones_fixtures()
        with autoindex:
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = client.get(url_for('api.zone_datasets', id=paca.id),
                              qs={'dynamic': 1})
        assert200(response)
        assert len(response.json) == 10

    def test_datasets_with_dynamic_region_and_size(self, autoindex, client):
        paca, bdr, arles = create_geozones_fixtures()
        with autoindex:
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = client.get(url_for('api.zone_datasets', id=paca.id),
                              qs={'dynamic': 1, 'size': 2})
        assert200(response)
        assert len(response.json) == 9

    def test_datasets_without_dynamic_region(self, autoindex, client):
        paca, bdr, arles = create_geozones_fixtures()
        with autoindex:
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[paca.id]))

        response = client.get(url_for('api.zone_datasets', id=paca.id))
        assert200(response)
        assert len(response.json) == 3

    def test_datasets_with_dynamic_county(self, autoindex, client):
        paca, bdr, arles = create_geozones_fixtures()
        with autoindex:
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[bdr.id]))

        response = client.get(url_for('api.zone_datasets', id=bdr.id),
                              qs={'dynamic': 1})
        assert200(response)
        assert len(response.json) == 10

    def test_datasets_with_dynamic_town(self, autoindex, client):
        paca, bdr, arles = create_geozones_fixtures()
        with autoindex:
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[arles.id]))

        response = client.get(url_for('api.zone_datasets', id=arles.id),
                              qs={'dynamic': 1})
        assert200(response)
        assert len(response.json) == 12

    def test_zone_children(self, client):
        paca, bdr, arles = create_geozones_fixtures()

        response = client.get(url_for('api.zone_children', id=paca.id))
        assert200(response)
        assert response.json['features'][0]['id'] == bdr.id

        response = client.get(url_for('api.zone_children', id=bdr.id))
        assert200(response)
        assert response.json['features'][0]['id'] == arles.id

        response = client.get(url_for('api.zone_children', id=arles.id))
        assert200(response)
        assert response.json['features'] == []


class SitemapTest:
    settings = GouvFrSettings
    modules = []

    def test_urls_within_sitemap(self, client):
        '''It should add gouvfr pages to sitemap.'''
        response = client.get('sitemap.xml')
        assert200(response)

        urls = [
            url_for('gouvfr.redevances_redirect', _external=True),
            url_for('gouvfr.faq_redirect', _external=True),
        ]
        for section in ('citizen', 'producer', 'reuser', 'developer',
                        'system-integrator'):
            urls.append(url_for('gouvfr.faq_redirect',
                                section=section, _external=True))

        for url in urls:
            assert '<loc>{url}</loc>'.format(url=url) in response.data


class SitemapTerritoriesTest:
    settings = TerritoriesSettings
    modules = []

    def test_towns_within_sitemap(self, sitemap):
        '''It should return the towns from the sitemap.'''
        paca, bdr, arles = create_geozones_fixtures()
        sitemap.fetch()
        url = sitemap.get_by_url('territories.territory', territory=arles)
        assert url is not None
        sitemap.assert_url(url, 0.5, 'weekly')

    def test_counties_within_sitemap(self, sitemap):
        '''It should return the counties from the sitemap.'''
        paca, bdr, arles = create_geozones_fixtures()
        sitemap.fetch()
        url = sitemap.get_by_url('territories.territory', territory=bdr)
        assert url is not None
        sitemap.assert_url(url, 0.5, 'weekly')

    def test_regions_within_sitemap(self, sitemap):
        '''It should return the regions from the sitemap.'''
        paca, bdr, arles = create_geozones_fixtures()
        sitemap.fetch()
        url = sitemap.get_by_url('territories.territory', territory=paca)
        assert url is not None
        sitemap.assert_url(url, 0.5, 'weekly')
