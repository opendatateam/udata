# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from flask import url_for
from lxml import etree

from udata import frontend, api
from udata.tests import TestCase, WebTestMixin, SearchTestMixin
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.post.factories import PostFactory
from udata.core.reuse.factories import VisibleReuseFactory
from udata.core.topic.factories import TopicFactory


# Neede for lxml XPath not supporting default namespace
NAMESPACES = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}


class SitemapTestCase(WebTestMixin, SearchTestMixin, TestCase):

    def create_app(self):
        app = super(SitemapTestCase, self).create_app()
        frontend.init_app(app)
        api.init_app(app)
        return app

    def get_sitemap_tree(self):
        response = self.get('sitemap.xml')
        self.assert200(response)
        self.sitemap = etree.fromstring(response.data)
        return self.sitemap

    def xpath(self, query):
        return self.sitemap.xpath(query, namespaces=NAMESPACES)

    def get_by_url(self, endpoint, **kwargs):
        url = url_for(endpoint, _external=True, **kwargs)
        query = 's:url[s:loc="{url}"]'.format(url=url)
        result = self.xpath(query)
        return result[0] if result else None

    def assert_url(self, url, priority, changefreq):
        r = url.xpath('s:priority', namespaces=NAMESPACES)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].text, str(priority))

        r = url.xpath('s:changefreq', namespaces=NAMESPACES)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].text, changefreq)


class SitemapTest(SitemapTestCase):

    def test_topics_within_sitemap(self):
        '''It should return a topic list from the sitemap.'''
        topics = TopicFactory.create_batch(3)

        self.get_sitemap_tree()

        for topic in topics:
            url = self.get_by_url('topics.display_redirect', topic=topic)
            self.assertIsNotNone(url)
            self.assert_url(url, 0.8, 'weekly')

    def test_organizations_within_sitemap(self):
        '''It should return an organization list from the sitemap.'''
        organizations = OrganizationFactory.create_batch(3)

        self.get_sitemap_tree()

        for org in organizations:
            url = self.get_by_url('organizations.show_redirect', org=org)
            self.assertIsNotNone(url)
            self.assert_url(url, 0.7, 'weekly')

    def test_reuses_within_sitemap(self):
        '''It should return a reuse list from the sitemap.'''
        reuses = VisibleReuseFactory.create_batch(3)

        self.get_sitemap_tree()

        for reuse in reuses:
            url = self.get_by_url('reuses.show_redirect', reuse=reuse)
            self.assertIsNotNone(url)
            self.assert_url(url, 0.8, 'weekly')

    def test_datasets_within_sitemap(self):
        '''It should return a dataset list from the sitemap.'''
        datasets = VisibleDatasetFactory.create_batch(3)

        self.get_sitemap_tree()

        for dataset in datasets:
            url = self.get_by_url('datasets.show_redirect', dataset=dataset)
            self.assertIsNotNone(url)
            self.assert_url(url, 0.8, 'weekly')

    def test_posts_within_sitemap(self):
        '''It should return a post list from the sitemap.'''
        posts = PostFactory.create_batch(3)

        self.get_sitemap_tree()

        for post in posts:
            url = self.get_by_url('posts.show_redirect', post=post)
            self.assertIsNotNone(url)
            self.assert_url(url, 0.6, 'weekly')

    def test_home_within_sitemap(self):
        '''It should return the home page from the sitemap.'''
        self.get_sitemap_tree()

        url = self.get_by_url('site.home_redirect')
        self.assertIsNotNone(url)
        self.assert_url(url, 1, 'daily')

    def test_dashboard_within_sitemap(self):
        '''It should return the dashoard page from the sitemap.'''
        self.get_sitemap_tree()

        url = self.get_by_url('site.dashboard_redirect')
        self.assertIsNotNone(url)
        self.assert_url(url, 0.6, 'weekly')

    def test_apidoc_within_sitemap(self):
        '''It should return the API Doc page from the sitemap.'''
        self.get_sitemap_tree()

        url = self.get_by_url('apidoc.swaggerui_redirect')
        self.assertIsNotNone(url)
        self.assert_url(url, 0.9, 'weekly')

    def test_terms_within_sitemap(self):
        '''It should return the terms page from the sitemap.'''
        self.get_sitemap_tree()

        url = self.get_by_url('site.terms_redirect')
        self.assertIsNotNone(url)
