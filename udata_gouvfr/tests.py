# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from tempfile import NamedTemporaryFile

from flask import url_for

from udata.tests import TestCase, DBTestMixin
from udata.tests.factories import DatasetFactory, ReuseFactory, OrganizationFactory
from udata.tests.frontend import FrontTestCase
from udata.settings import Testing

from udata.ext import cow

from .commands import certify
from .metrics import PublicServicesMetric


class GouvFrSettings(Testing):
    TEST_WITH_THEME = True
    TEST_WITH_PLUGINS = True
    PLUGINS = ['cow', 'gouvfr']
    THEME = 'gouvfr'


class GouvFrThemeTest(FrontTestCase):
    '''Ensure themed views render'''
    settings = GouvFrSettings

    def create_app(self):
        app = super(GouvFrThemeTest, self).create_app()
        cow.init_app(app)
        return app

    def test_render_home(self):
        '''It should render the home page'''
        with self.autoindex():
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organzation=org)
                ReuseFactory(organzation=org)

        response = self.get(url_for('front.home'))
        self.assert200(response)

    def test_render_home_no_data(self):
        '''It should render the home page without data'''
        response = self.get(url_for('front.home'))
        self.assert200(response)

    def test_render_search(self):
        '''It should render the search page'''
        with self.autoindex():
            for i in range(3):
                org = OrganizationFactory()
                DatasetFactory(organzation=org)
                ReuseFactory(organzation=org)

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
            DatasetFactory(organzation=org)
            ReuseFactory(organzation=org)
        response = self.get(url_for('site.metrics'))
        self.assert200(response)

    def test_render_metrics_no_data(self):
        '''It should render the search page without data'''
        response = self.get(url_for('site.metrics'))
        self.assert200(response)

    def test_render_dataset_page(self):
        '''It should render the dataset page'''
        org = OrganizationFactory()
        dataset = DatasetFactory(organzation=org)
        ReuseFactory(organzation=org, datasets=[dataset])

        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assert200(response)

    def test_render_organization_page(self):
        '''It should render the organization page'''
        org = OrganizationFactory()
        datasets = [DatasetFactory(organzation=org) for _ in range(3)]
        reuses = [ReuseFactory(organzation=org, datasets=[d]) for d in datasets]

        response = self.get(url_for('organizations.show', org=org))
        self.assert200(response)

    def test_render_reuse_page(self):
        '''It should render the reuse page'''
        org = OrganizationFactory()
        dataset = DatasetFactory(organzation=org)
        reuse = ReuseFactory(organzation=org, datasets=[dataset])

        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert200(response)


class GouvFrMetricsTest(DBTestMixin, TestCase):
    '''Check metrics'''
    settings = GouvFrSettings

    def test_public_services(self):
        public_services = [OrganizationFactory(public_service=True) for _ in range(2)]
        for _ in range(3):
            OrganizationFactory(public_service=False)

        self.assertEqual(PublicServicesMetric().get_value(), len(public_services))


class CertifyCommandTest(DBTestMixin, TestCase):
    settings = GouvFrSettings

    def test_certify_by_id(self):
        org = OrganizationFactory()

        certify(str(org.id))

        org.reload()
        self.assertTrue(org.public_service)

    def test_certify_from_file(self):
        orgs = [OrganizationFactory() for _ in range(2)]

        with NamedTemporaryFile() as temp:
            temp.write('\n'.join((str(org.id) for org in orgs)))
            temp.flush()

            certify(temp.name)

        for org in orgs:
            org.reload()
            self.assertTrue(org.public_service)


class LegacyUrlsTest(FrontTestCase):
    settings = GouvFrSettings

    def create_app(self):
        app = super(LegacyUrlsTest, self).create_app()
        cow.init_app(app)
        app.config['DEFAULT_LANGUAGE'] = 'en'
        return app

    def test_redirect_datasets(self):
        dataset = DatasetFactory()
        response = self.client.get('/en/dataset/%s/' % dataset.slug)
        self.assertRedirects(response, url_for('datasets.show', dataset=dataset))

    def test_redirect_organizations(self):
        org = OrganizationFactory()
        response = self.client.get('/en/organization/%s/' % org.slug)
        self.assertRedirects(response, url_for('organizations.show', org=org))


class SpecificUrlsTest(FrontTestCase):
    settings = GouvFrSettings

    def create_app(self):
        app = super(SpecificUrlsTest, self).create_app()
        cow.init_app(app)
        return app

    def test_redevances(self):
        response = self.client.get(url_for('gouvfr.redevances'))
        self.assert200(response)

    def test_developer(self):
        response = self.client.get(url_for('gouvfr.developer'))
        self.assert200(response)
