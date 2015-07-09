# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import OrganizationBadge, PUBLIC_SERVICE
from udata.tests import TestCase, DBTestMixin
from udata.tests.factories import DatasetFactory, ReuseFactory, OrganizationFactory
from udata.tests.factories import VisibleReuseFactory
from udata.tests.frontend import FrontTestCase
from udata.settings import Testing

from .views import DATACONNEXIONS_CATEGORIES, DATACONNEXIONS_TAG

from .metrics import PublicServicesMetric


class GouvFrSettings(Testing):
    TEST_WITH_THEME = True
    TEST_WITH_PLUGINS = True
    PLUGINS = ['gouvfr']
    THEME = 'gouvfr'


class GouvFrThemeTest(FrontTestCase):
    '''Ensure themed views render'''
    settings = GouvFrSettings

    def test_render_home(self):
        '''It should render the home page'''
        with self.autoindex():
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organization=org)
                ReuseFactory(organization=org)

        response = self.get(url_for('site.home'))
        self.assert200(response)

    def test_render_home_no_data(self):
        '''It should render the home page without data'''
        response = self.get(url_for('site.home'))
        self.assert200(response)

    def test_render_search(self):
        '''It should render the search page'''
        with self.autoindex():
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organization=org)
                ReuseFactory(organization=org)

        response = self.get(url_for('front.search'))
        self.assert200(response)

    def test_render_search_no_data(self):
        '''It should render the search page without data'''
        response = self.get(url_for('front.search'))
        self.assert200(response)

    def test_render_metrics(self):
        '''It should render the search page'''
        for i in range(3):
            org = OrganizationFactory()
            DatasetFactory(organization=org)
            ReuseFactory(organization=org)
        response = self.get(url_for('site.dashboard'))
        self.assert200(response)

    def test_render_metrics_no_data(self):
        '''It should render the search page without data'''
        response = self.get(url_for('site.dashboard'))
        self.assert200(response)

    def test_render_dataset_page(self):
        '''It should render the dataset page'''
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        ReuseFactory(organization=org, datasets=[dataset])

        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assert200(response)

    def test_render_organization_page(self):
        '''It should render the organization page'''
        org = OrganizationFactory()
        datasets = [DatasetFactory(organization=org) for _ in range(3)]
        reuses = [ReuseFactory(organization=org, datasets=[d]) for d in datasets]

        response = self.get(url_for('organizations.show', org=org))
        self.assert200(response)

    def test_render_reuse_page(self):
        '''It should render the reuse page'''
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)
        reuse = ReuseFactory(organization=org, datasets=[dataset])

        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert200(response)


class GouvFrMetricsTest(DBTestMixin, TestCase):
    '''Check metrics'''
    settings = GouvFrSettings

    def test_public_services(self):
        ps_badge = OrganizationBadge(kind=PUBLIC_SERVICE)
        public_services = [
            OrganizationFactory(badges=[ps_badge]) for _ in range(2)
        ]
        for _ in range(3):
            OrganizationFactory()

        self.assertEqual(PublicServicesMetric().get_value(), len(public_services))


class LegacyUrlsTest(FrontTestCase):
    settings = GouvFrSettings

    def create_app(self):
        app = super(LegacyUrlsTest, self).create_app()
        app.config['DEFAULT_LANGUAGE'] = 'en'
        return app

    def test_redirect_datasets(self):
        dataset = DatasetFactory()
        response = self.client.get('/en/dataset/%s/' % dataset.slug)
        self.assertRedirects(response, url_for('datasets.show', dataset=dataset))

    def test_redirect_datasets_not_found(self):
        response = self.client.get('/en/DataSet/wtf')
        self.assert404(response)

    def test_redirect_organizations(self):
        org = OrganizationFactory()
        response = self.client.get('/en/organization/%s/' % org.slug)
        self.assertRedirects(response, url_for('organizations.show', org=org))

    def test_redirect_organization_list(self):
        response = self.client.get('/en/organization/')
        self.assertRedirects(response, url_for('organizations.list'))

    def test_redirect_topics(self):
        response = self.client.get('/en/group/societe/')
        self.assertRedirects(response, url_for('topics.display', topic='societe'))


class SpecificUrlsTest(FrontTestCase):
    settings = GouvFrSettings

    def test_redevances(self):
        response = self.client.get(url_for('gouvfr.redevances'))
        self.assert200(response)

    def test_faq_home(self):
        response = self.client.get(url_for('gouvfr.faq'))
        self.assert200(response)
        self.assert_template_used('faq/home.html')

    def test_citizen_faq(self):
        response = self.client.get(url_for('gouvfr.faq', section='citizen'))
        self.assert200(response)
        self.assert_template_used('faq/citizen.html')

    def test_producer_faq(self):
        response = self.client.get(url_for('gouvfr.faq', section='producer'))
        self.assert200(response)
        self.assert_template_used('faq/producer.html')

    def test_reuser_faq(self):
        response = self.client.get(url_for('gouvfr.faq', section='reuser'))
        self.assert200(response)
        self.assert_template_used('faq/reuser.html')

    def test_developer_faq(self):
        response = self.client.get(url_for('gouvfr.faq', section='developer'))
        self.assert200(response)
        self.assert_template_used('faq/developer.html')

    def test_terms(self):
        response = self.client.get(url_for('gouvfr.terms'))
        self.assert200(response)

    def test_credits(self):
        response = self.client.get(url_for('gouvfr.credits'))
        self.assert200(response)


class DataconnexionsTest(FrontTestCase):
    settings = GouvFrSettings

    def test_render_dataconnexions_without_data(self):
        response = self.client.get(url_for('gouvfr.dataconnexions'))
        self.assert200(response)

    def test_render_dataconnexions_with_data(self):
        for tag, label, description in DATACONNEXIONS_CATEGORIES:
            VisibleReuseFactory(tags=[DATACONNEXIONS_TAG, tag])
        response = self.client.get(url_for('gouvfr.dataconnexions'))
        self.assert200(response)


class C3Test(FrontTestCase):
    settings = GouvFrSettings

    def test_redirect_c3(self):
        response = self.client.get(url_for('gouvfr.c3'))
        self.assertRedirects(response, '/en/climate-change-challenge')

    def test_render_c3_without_data(self):
        response = self.client.get(url_for('gouvfr.climate_change_challenge'))
        self.assert200(response)


class SitemapTest(FrontTestCase):
    settings = GouvFrSettings

    def test_urls_within_sitemap(self):
        '''It should add gouvfr pages to sitemap.'''
        response = self.get('sitemap.xml')
        self.assert200(response)

        urls = [
            url_for('gouvfr.credits_redirect', _external=True),
            url_for('gouvfr.terms_redirect', _external=True),
            url_for('gouvfr.redevances_redirect', _external=True),
            url_for('gouvfr.faq_redirect', _external=True),
        ]
        for section in ('citizen', 'producer', 'reuser', 'developer'):
            urls.append(url_for('gouvfr.faq_redirect', section='citizen', _external=True))

        for url in urls:
            self.assertIn('<loc>{url}</loc>'.format(url=url), response.data)
