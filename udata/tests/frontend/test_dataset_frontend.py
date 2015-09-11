# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
import feedparser
from flask import url_for

from udata.models import FollowDataset

from . import FrontTestCase
from ..factories import (
    ResourceFactory, DatasetFactory, UserFactory, OrganizationFactory
)


class DatasetBlueprintTest(FrontTestCase):
    def test_render_list(self):
        '''It should render the dataset list page'''
        with self.autoindex():
            datasets = [DatasetFactory(
                resources=[ResourceFactory()]) for i in range(3)]

        response = self.get(url_for('datasets.list'))

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), len(datasets))

    def test_render_list_with_query(self):
        '''It should render the dataset list page with a query string'''
        with self.autoindex():
            datasets = [DatasetFactory(
                resources=[ResourceFactory()]) for i in range(3)]
            expected_dataset = DatasetFactory(
                title='test for query', resources=[ResourceFactory()])
            datasets.append(expected_dataset)

        response = self.get(url_for('datasets.list'),
                            qs={'q': 'test for query'})

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), 1)
        self.assertEqual(rendered_datasets[0].id, expected_dataset.id)

    def test_render_list_empty(self):
        '''It should render the dataset list page event if empty'''
        response = self.get(url_for('datasets.list'))
        self.assert200(response)

    def test_render_display(self):
        '''It should render the dataset page'''
        dataset = DatasetFactory()
        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assert200(response)

    def test_raise_404_if_private(self):
        '''It should raise a 404 if the dataset is private'''
        dataset = DatasetFactory(private=True)
        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assert404(response)

    def test_raise_410_if_deleted(self):
        '''It should raise a 410 if the dataset is deleted'''
        dataset = DatasetFactory(deleted=datetime.now())
        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assertStatus(response, 410)

    def test_200_if_deleted_but_authorized(self):
        '''It should not raise a 410 if the can view it'''
        self.login()
        dataset = DatasetFactory(deleted=datetime.now(), owner=self.user)
        response = self.get(url_for('datasets.show', dataset=dataset))
        self.assert200(response)

    def test_not_found(self):
        '''It should render the dataset page'''
        response = self.get(url_for('datasets.show', dataset='not-found'))
        self.assert404(response)

    def test_recent_feed(self):
        datasets = [DatasetFactory(
            resources=[ResourceFactory()]) for i in range(3)]

        response = self.get(url_for('datasets.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), len(datasets))
        for i in range(1, len(feed.entries)):
            published_date = feed.entries[i].published_parsed
            prev_published_date = feed.entries[i - 1].published_parsed
            self.assertGreaterEqual(prev_published_date, published_date)

    def test_recent_feed_owner(self):
        owner = UserFactory()
        DatasetFactory(owner=owner, resources=[ResourceFactory()])

        response = self.get(url_for('datasets.recent_feed'))

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
        DatasetFactory(
            owner=owner, organization=org, resources=[ResourceFactory()])

        response = self.get(url_for('datasets.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, org.name)
        self.assertEqual(author.href,
                         self.full_url('organizations.show', org=org.id))

    def test_dataset_followers(self):
        '''It should render the dataset followers list page'''
        dataset = DatasetFactory()
        followers = [
            FollowDataset.objects.create(follower=UserFactory(),
                                         following=dataset) for _ in range(3)]

        response = self.get(url_for('datasets.followers', dataset=dataset))

        self.assert200(response)
        rendered_followers = self.get_context_variable('followers')
        self.assertEqual(len(rendered_followers), len(followers))
