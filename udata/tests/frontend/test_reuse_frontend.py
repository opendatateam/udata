# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

import feedparser

from flask import url_for

from udata.models import Reuse, Member

from . import FrontTestCase
from ..factories import ReuseFactory, UserFactory, AdminFactory, OrganizationFactory, DatasetFactory


class ReuseBlueprintTest(FrontTestCase):
    def test_render_list(self):
        '''It should render the reuse list page'''
        with self.autoindex():
            reuses = [ReuseFactory(datasets=[DatasetFactory()]) for i in range(3)]

        response = self.get(url_for('reuses.list'))

        self.assert200(response)
        rendered_reuses = self.get_context_variable('reuses')
        self.assertEqual(rendered_reuses.total, len(reuses))

    def test_render_list_with_query(self):
        '''It should render the reuse list page with a query'''
        with self.autoindex():
            [ReuseFactory(title='Reuse {0}'.format(i), datasets=[DatasetFactory()]) for i in range(3)]

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

    def test_render_create_with_dataset(self):
        '''It should render the reuse create form with preentered dataset'''
        dataset = DatasetFactory()
        response = self.get(url_for('reuses.new', dataset=str(dataset.id)))
        self.assert200(response)
        form = self.get_context_variable('form')
        self.assertEqual(form.datasets.data, [dataset])

    def test_render_create_with_dataset_does_not_fails(self):
        '''It should render the reuse create form without failing with an unknown dataset'''
        response = self.get(url_for('reuses.new', dataset='not-found'))
        self.assert200(response)

    def test_create(self):
        '''It should create a reuse and redirect to reuse page'''
        data = ReuseFactory.attributes()
        self.login()
        response = self.post(url_for('reuses.new'), data)

        reuse = Reuse.objects.first()
        self.assertRedirects(response, reuse.display_url)
        self.assertEqual(reuse.owner, self.user)
        self.assertIsNone(reuse.organization)

    def test_create_as_org(self):
        '''It should create a reuse and redirect to reuse page'''
        self.login()
        member = Member(user=self.user, role='editor')
        org = OrganizationFactory(members=[member])
        data = ReuseFactory.attributes()
        data['organization'] = str(org.id)
        response = self.post(url_for('reuses.new'), data)

        reuse = Reuse.objects.first()
        self.assertRedirects(response, reuse.display_url)
        self.assertEqual(reuse.organization, org)
        self.assertIsNone(reuse.owner)

    def test_create_as_org_permissions(self):
        '''It should create a reuse and redirect to reuse page'''
        org = OrganizationFactory()
        data = ReuseFactory.attributes()
        data['organization'] = str(org.id)
        self.login()
        response = self.post(url_for('reuses.new'), data)

        self.assert403(response)
        self.assertEqual(Reuse.objects.count(), 0)

    def test_create_url_exists(self):
        '''It should fail create a reuse if URL exists'''
        reuse = ReuseFactory()
        data = ReuseFactory.attributes()
        data['url'] = reuse.url
        self.login()
        response = self.post(url_for('reuses.new'), data)

        self.assert200(response)  # Does not redirect on success
        self.assertEqual(len(Reuse.objects), 1)

    def test_render_display(self):
        '''It should render the reuse page'''
        reuse = ReuseFactory()
        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert200(response)

    def test_raise_404_if_private(self):
        '''It should raise a 404 if the reuse is private'''
        reuse = ReuseFactory(private=True)
        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assert404(response)

    def test_raise_410_if_deleted(self):
        '''It should raise a 410 if the reuse is deleted'''
        reuse = ReuseFactory(deleted=datetime.now())
        response = self.get(url_for('reuses.show', reuse=reuse))
        self.assertStatus(response, 410)

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
        self.assertRedirects(response, reuse.display_url)
        self.assertEqual(reuse.description, 'new description')

    def test_delete(self):
        '''It should handle deletion from form submit and redirect on reuse page'''
        self.login(AdminFactory())
        reuse = ReuseFactory()
        response = self.post(url_for('reuses.delete', reuse=reuse))

        reuse.reload()
        self.assertRedirects(response, reuse.display_url)
        self.assertIsNotNone(reuse.deleted)

    def test_render_transfer(self):
        '''It should render the reuse transfer form'''
        user = self.login()
        reuse = ReuseFactory(owner=user)
        response = self.get(url_for('reuses.transfer', reuse=reuse))
        self.assert200(response)

    def test_not_found(self):
        '''It should render the reuse page'''
        response = self.get(url_for('reuses.show', reuse='not-found'))
        self.assert404(response)

    def test_recent_feed(self):
        datasets = [ReuseFactory(datasets=[DatasetFactory()]) for i in range(3)]

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
        self.assertEqual(author.href, self.full_url('users.show', user=owner.id))

    def test_recent_feed_org(self):
        owner = UserFactory()
        org = OrganizationFactory()
        ReuseFactory(owner=owner, organization=org, datasets=[DatasetFactory()])

        response = self.get(url_for('reuses.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, org.name)
        self.assertEqual(author.href, self.full_url('organizations.show', org=org.id))

    def test_render_issues(self):
        '''It should render the reuse issues page'''
        self.login(AdminFactory())
        reuse = ReuseFactory()
        response = self.get(url_for('reuses.issues', reuse=reuse))
        self.assert200(response)

    def test_add_dataset_to_reuse(self):
        '''It should add the dataset to the reuse and redirect its page'''
        self.login(AdminFactory())
        reuse = ReuseFactory()
        dataset = DatasetFactory()
        data = {'dataset': str(dataset.id)}
        response = self.post(url_for('reuses.add_dataset', reuse=reuse), data)

        reuse.reload()
        self.assertRedirects(response, reuse.display_url)
        self.assertIn(dataset, reuse.datasets)

    def test_add_non_existant_dataset_to_reuse(self):
        '''It should not add a non existant dataset to the reuse and redirect its edit page'''
        self.login(AdminFactory())
        reuse = ReuseFactory()
        data = {'dataset': 'not-found'}
        response = self.post(url_for('reuses.add_dataset', reuse=reuse), data)

        reuse.reload()
        self.assertRedirects(response, url_for('reuses.edit', reuse=reuse))
