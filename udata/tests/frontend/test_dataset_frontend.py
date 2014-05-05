# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import feedparser
import StringIO
import unicodecsv

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
        self.assertRedirects(response, url_for('datasets.show', dataset=dataset))

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
        self.assertRedirects(response, dataset.get_absolute_url())
        self.assertEqual(dataset.description, 'new description')

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
