# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import feedparser

from flask import url_for

from udata.models import Reuse

from . import FrontTestCase
from ..factories import ReuseFactory, UserFactory, AdminFactory, OrganizationFactory


class ReuseBlueprintTest(FrontTestCase):
    def test_render_list(self):
        '''It should render the reuse list page'''
        with self.autoindex():
            reuses = [ReuseFactory() for i in range(3)]

        response = self.get(url_for('reuses.list'))

        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        print rendered_reuses
        self.assertEqual(rendered_reuses.total, len(reuses))

    def test_render_list_with_query(self):
        '''It should render the reuse list page with a query'''
        with self.autoindex():
            [ReuseFactory(title='Reuse {0}'.format(i)) for i in range(3)]

        response = self.get(url_for('reuses.list'), qs={'q': '2'})

        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(rendered_reuses.total, 1)

    def test_render_list_empty(self):
        '''It should render the reuse list page event if empty'''
        response = self.get(url_for('reuses.list'))
        self.assert200(response)

    def test_render_create(self):
        '''It should render the reuse create form'''
        response = self.get(url_for('reuses.new'))
        self.assert200(response)

    def test_create(self):
        '''It should create a reuse and redirect to reuse page'''
        data = ReuseFactory.attributes()
        self.login()
        response = self.post(url_for('reuses.new'), data)

        reuse = Reuse.objects.first()
        self.assertRedirects(response, reuse.get_absolute_url())

    def test_render_display(self):
        '''It should render the reuse page'''
        reuse = ReuseFactory()
        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert200(response)

    def test_render_edit(self):
        '''It should render the reuse edit form'''
        self.login(AdminFactory())
        reuse = ReuseFactory()
        response = self.get(url_for('reuses.edit', reuse=reuse))
        self.assert200(response)

    def test_edit(self):
        '''It should handle edit form submit and redirect on reuse page'''
        self.login(AdminFactory())
        reuse = ReuseFactory()
        data = reuse.to_dict()
        data['description'] = 'new description'
        response = self.post(url_for('reuses.edit', reuse=reuse), data)

        reuse.reload()
        self.assertRedirects(response, reuse.get_absolute_url())
        self.assertEqual(reuse.description, 'new description')

    def test_not_found(self):
        '''It should render the reuse page'''
        response = self.get(url_for('reuses.show', reuse='not-found'))
        self.assert404(response)

    def test_recent_feed(self):
        datasets = [ReuseFactory() for i in range(3)]

        response = self.get(url_for('reuses.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), len(datasets))
        for i in range(1, len(feed.entries)):
            published_date = feed.entries[i].published_parsed
            prev_published_date = feed.entries[i - 1].published_parsed
            self.assertGreaterEqual(published_date, prev_published_date)

    def test_recent_feed_owner(self):
        owner = UserFactory()
        ReuseFactory(owner=owner)

        response = self.get(url_for('reuses.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, owner.fullname)
        self.assertEqual(author.href, self.full_url('users.show', user=owner))

    def test_recent_feed_org(self):
        owner = UserFactory()
        org = OrganizationFactory()
        ReuseFactory(owner=owner, organization=org)

        response = self.get(url_for('reuses.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, org.name)
        self.assertEqual(author.href, self.full_url('organizations.show', org=org))
