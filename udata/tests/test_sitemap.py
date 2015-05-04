# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata import frontend
from udata.tests import TestCase, WebTestMixin, SearchTestMixin

from .factories import TopicFactory, OrganizationFactory, VisibleReuseFactory, VisibleDatasetFactory


class SitemapTestCase(WebTestMixin, SearchTestMixin, TestCase):

    def create_app(self):
        app = super(SitemapTestCase, self).create_app()
        frontend.init_app(app)
        return app


class SitemapTest(SitemapTestCase):

    def test_topics_within_sitemap(self):
        '''It should return a topic list from the sitemap.'''
        topics = TopicFactory.create_batch(3)
        response = self.get('sitemap.xml')
        self.assert200(response)
        self.assertEqual(response.data.count('<loc>'), 3, response.data)
        self.assertIn('<priority>0.8</priority>', response.data)
        self.assertIn('<changefreq>weekly</changefreq>', response.data)
        self.assertIn(
            '<loc>http://localhost/topics/{topic}/</loc>'.format(topic=topics[0].slug),
            response.data)

    def test_organizations_within_sitemap(self):
        '''It should return an organization list from the sitemap.'''
        organizations = OrganizationFactory.create_batch(3)
        response = self.get('sitemap.xml')
        self.assert200(response)
        self.assertEqual(response.data.count('<loc>'), 3, response.data)
        self.assertIn('<priority>0.8</priority>', response.data)
        self.assertIn('<changefreq>weekly</changefreq>', response.data)
        self.assertIn(
            '<loc>http://localhost/organizations/{organization}/</loc>'.format(organization=organizations[0].slug),
            response.data)

    def test_reuses_within_sitemap(self):
        '''It should return a reuse list from the sitemap.'''
        reuses = VisibleReuseFactory.create_batch(3)
        response = self.get('sitemap.xml')
        self.assert200(response)
        self.assertEqual(response.data.count('<loc>'), 3, response.data)
        self.assertIn('<priority>0.8</priority>', response.data)
        self.assertIn('<changefreq>weekly</changefreq>', response.data)
        self.assertIn(
            '<loc>http://localhost/reuses/{reuse}/</loc>'.format(reuse=reuses[0].slug),
            response.data)

    def test_datasets_within_sitemap(self):
        '''It should return a dataset list from the sitemap.'''
        datasets = VisibleDatasetFactory.create_batch(3)
        response = self.get('sitemap.xml')
        self.assert200(response)
        self.assertEqual(response.data.count('<loc>'), 3, response.data)
        self.assertIn('<priority>1</priority>', response.data)
        self.assertIn('<changefreq>weekly</changefreq>', response.data)
        self.assertIn(
            '<loc>http://localhost/datasets/{dataset}/</loc>'.format(dataset=datasets[0].id),
            response.data)
