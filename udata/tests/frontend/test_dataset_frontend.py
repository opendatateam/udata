# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import feedparser

from flask import url_for

from udata.models import Dataset

from . import FrontTestCase
from ..factories import ResourceFactory, DatasetFactory, UserFactory, OrganizationFactory


class DatasetBlueprintTest(FrontTestCase):
    def test_render_list(self):
        '''It should render the dataset list page'''
        with self.autoindex():
            datasets = [DatasetFactory() for i in range(3)]

        response = self.get(url_for('datasets.list'))

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), len(datasets))

    def test_render_list_with_query(self):
        '''It should render the dataset list page with a query string'''
        with self.autoindex():
            datasets = [DatasetFactory() for i in range(3)]
            expected_dataset = DatasetFactory(title='test for query')
            datasets.append(expected_dataset)

        response = self.get(url_for('datasets.list'), qs={'q': 'test for query'})

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), 1)
        self.assertEqual(rendered_datasets[0].id, expected_dataset.id)

    def test_render_list_empty(self):
        '''It should render the dataset list page event if empty'''
        response = self.get(url_for('datasets.list'))
        self.assert200(response)

    def test_render_create(self):
        '''It should render the dataset create form'''
        response = self.get(url_for('datasets.new'))
        self.assert200(response)

    def test_create(self):
        '''It should create a dataset and redirect to dataset page'''
        data = DatasetFactory.attributes()
        self.login()
        response = self.post(url_for('datasets.new'), data)

        dataset = Dataset.objects.first()
        self.assertRedirects(response, url_for('datasets.new_resource', dataset=dataset))

        self.assertEqual(dataset.owner, self.user)
        self.assertIsNone(dataset.organization)

    def test_create_as_org(self):
        '''It should create a dataset as an organization and redirect to dataset page'''
        org = OrganizationFactory()
        data = DatasetFactory.attributes()
        data['organization'] = str(org.id)
        self.login()
        response = self.post(url_for('datasets.new'), data)

        dataset = Dataset.objects.first()
        self.assertRedirects(response, url_for('datasets.new_resource', dataset=dataset))

        self.assertIsNone(dataset.owner)
        self.assertEqual(dataset.organization, org)

    def test_render_display(self):
        '''It should render the dataset page'''
        dataset = DatasetFactory()
        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assert200(response)

    def test_render_edit(self):
        '''It should render the dataset edit form'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        response = self.get(url_for('datasets.edit', dataset=dataset))
        self.assert200(response)

    def test_edit(self):
        '''It should handle edit form submit and redirect on dataset page'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        data = dataset.to_dict()
        data['description'] = 'new description'
        response = self.post(url_for('datasets.edit', dataset=dataset), data)

        dataset.reload()
        self.assertRedirects(response, dataset.display_url)
        self.assertEqual(dataset.description, 'new description')

    def test_render_edit_extras(self):
        '''It should render the dataset extras edit form'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        response = self.get(url_for('datasets.edit_extras', dataset=dataset))
        self.assert200(response)

    def test_add_extras(self):
        user = self.login()
        dataset = DatasetFactory(owner=user)
        data = {'key': 'a_key', 'value': 'a_value'}

        response = self.post(url_for('datasets.edit_extras', dataset=dataset), data)

        self.assert200(response)
        dataset.reload()
        self.assertIn('a_key', dataset.extras)
        self.assertEqual(dataset.extras['a_key'], 'a_value')

    def test_update_extras(self):
        user = self.login()
        dataset = DatasetFactory(owner=user, extras={'a_key': 'a_value'})
        data = {'key': 'a_key', 'value': 'new_value'}

        response = self.post(url_for('datasets.edit_extras', dataset=dataset), data)

        self.assert200(response)
        dataset.reload()
        self.assertIn('a_key', dataset.extras)
        self.assertEqual(dataset.extras['a_key'], 'new_value')

    def test_rename_extras(self):
        user = self.login()
        dataset = DatasetFactory(owner=user, extras={'a_key': 'a_value'})
        data = {'key': 'new_key', 'value': 'a_value', 'old_key': 'a_key'}

        response = self.post(url_for('datasets.edit_extras', dataset=dataset), data)

        self.assert200(response)
        dataset.reload()
        self.assertIn('new_key', dataset.extras)
        self.assertEqual(dataset.extras['new_key'], 'a_value')
        self.assertNotIn('a_key', dataset.extras)

    def test_delete_extras(self):
        user = self.login()
        dataset = DatasetFactory(owner=user, extras={'a_key': 'a_value'})

        response = self.delete(url_for('datasets.delete_extra', dataset=dataset, extra='a_key'))

        self.assert200(response)
        dataset.reload()
        self.assertNotIn('a_key', dataset.extras)

    def test_render_edit_resources(self):
        '''It should render the dataset resouces edit form'''
        user = self.login()
        dataset = DatasetFactory(owner=user, resources=[ResourceFactory() for _ in range(3)])
        response = self.get(url_for('datasets.edit_resources', dataset=dataset))
        self.assert200(response)

    def test_render_transfer(self):
        '''It should render the dataset transfer form'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        response = self.get(url_for('datasets.transfer', dataset=dataset))
        self.assert200(response)

    def test_not_found(self):
        '''It should render the dataset page'''
        response = self.get(url_for('datasets.show', dataset='not-found'))
        self.assert404(response)

    def test_recent_feed(self):
        datasets = [DatasetFactory() for i in range(3)]

        response = self.get(url_for('datasets.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), len(datasets))
        for i in range(1, len(feed.entries)):
            published_date = feed.entries[i].published_parsed
            prev_published_date = feed.entries[i - 1].published_parsed
            self.assertGreaterEqual(published_date, prev_published_date)

    def test_recent_feed_owner(self):
        owner = UserFactory()
        DatasetFactory(owner=owner)

        response = self.get(url_for('datasets.recent_feed'))

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
        DatasetFactory(owner=owner, organization=org)

        response = self.get(url_for('datasets.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, org.name)
        self.assertEqual(author.href, self.full_url('organizations.show', org=org))
