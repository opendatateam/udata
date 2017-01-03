# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import feedparser

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory
from udata.core.organization.factories import OrganizationFactory

from . import FrontTestCase


class ReuseBlueprintTest(FrontTestCase):
    def test_render_list(self):
        '''It should render the reuse list page'''
        with self.autoindex():
            reuses = [
                ReuseFactory(datasets=[DatasetFactory()]) for i in range(3)]

        response = self.get(url_for('reuses.list'))

        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(rendered_reuses.total, len(reuses))

    def test_render_list_with_query(self):
        '''It should render the reuse list page with a query'''
        with self.autoindex():
            [ReuseFactory(
                title='Reuse {0}'.format(i), datasets=[DatasetFactory()])
             for i in range(3)]

        response = self.get(url_for('reuses.list'), qs={'q': '2'})

        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(rendered_reuses.total, 1)

    def test_render_list_empty(self):
        '''It should render the reuse list page even if empty'''
        self.init_search()
        response = self.get(url_for('reuses.list'))
        self.assert200(response)

    def test_render_display(self):
        '''It should render the reuse page'''
        reuse = ReuseFactory(owner=UserFactory(),
                             description='* Title 1\n* Title 2')
        url = url_for('reuses.show', reuse=reuse)
        response = self.get(url)
        self.assert200(response)
        json_ld = self.get_json_ld(response)
        self.assertEquals(json_ld['@context'], 'http://schema.org')
        self.assertEquals(json_ld['@type'], 'CreativeWork')
        self.assertEquals(json_ld['alternateName'], reuse.slug)
        self.assertEquals(json_ld['dateCreated'][:16],
                          reuse.created_at.isoformat()[:16])
        self.assertEquals(json_ld['dateModified'][:16],
                          reuse.last_modified.isoformat()[:16])
        self.assertEquals(json_ld['url'], 'http://localhost{}'.format(url))
        self.assertEquals(json_ld['name'], reuse.title)
        self.assertEquals(json_ld['description'], 'Title 1 Title 2')
        self.assertEquals(json_ld['isBasedOnUrl'], reuse.url)
        self.assertEquals(json_ld['author']['@type'], 'Person')

    def test_raise_404_if_private(self):
        '''It should raise a 404 if the reuse is private'''
        reuse = ReuseFactory(private=True)
        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert404(response)

    def test_raise_410_if_deleted(self):
        '''It should raise a 410 if the reuse is deleted'''
        reuse = ReuseFactory(deleted=datetime.now())
        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert410(response)

    def test_do_not_raise_410_if_deleted_but_authorized(self):
        '''It should display a dalated reuse if authorized'''
        self.login()
        reuse = ReuseFactory(deleted=datetime.now(), owner=self.user)
        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert200(response)

    def test_not_found(self):
        '''It should render the reuse page'''
        response = self.get(url_for('reuses.show', reuse='not-found'))
        self.assert404(response)

    def test_recent_feed(self):
        datasets = [ReuseFactory(
                    datasets=[DatasetFactory()]) for i in range(3)]

        response = self.get(url_for('reuses.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), len(datasets))
        for i in range(1, len(feed.entries)):
            published_date = feed.entries[i].published_parsed
            prev_published_date = feed.entries[i - 1].published_parsed
            self.assertGreaterEqual(prev_published_date, published_date)

    def test_recent_feed_owner(self):
        owner = UserFactory()
        ReuseFactory(owner=owner, datasets=[DatasetFactory()])

        response = self.get(url_for('reuses.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, owner.fullname)
        self.assertEqual(author.href,
                         self.full_url('users.show', user=owner.id))

    def test_recent_feed_org(self):
        owner = UserFactory()
        org = OrganizationFactory()
        ReuseFactory(owner=owner,
                     organization=org, datasets=[DatasetFactory()])

        response = self.get(url_for('reuses.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, org.name)
        self.assertEqual(author.href,
                         self.full_url('organizations.show', org=org.id))
