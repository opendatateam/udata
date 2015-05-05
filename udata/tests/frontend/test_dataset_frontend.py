# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import mock
import feedparser

from datetime import datetime
from StringIO import StringIO

from flask import url_for
from flask.ext import fs

from udata.core import storages
from udata.models import Dataset, FollowDataset, Member

from . import FrontTestCase
from ..factories import ResourceFactory, DatasetFactory, UserFactory, OrganizationFactory


class DatasetBlueprintTest(FrontTestCase):
    def test_render_list(self):
        '''It should render the dataset list page'''
        with self.autoindex():
            datasets = [DatasetFactory(resources=[ResourceFactory()]) for i in range(3)]

        response = self.get(url_for('datasets.list'))

        self.assert200(response)
        rendered_datasets = self.get_context_variable('datasets')
        self.assertEqual(len(rendered_datasets), len(datasets))

    def test_render_list_with_query(self):
        '''It should render the dataset list page with a query string'''
        with self.autoindex():
            datasets = [DatasetFactory(resources=[ResourceFactory()]) for i in range(3)]
            expected_dataset = DatasetFactory(title='test for query', resources=[ResourceFactory()])
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
        self.login()
        member = Member(user=self.user, role='editor')
        org = OrganizationFactory(members=[member])
        data = DatasetFactory.attributes()
        data['organization'] = str(org.id)
        response = self.post(url_for('datasets.new'), data)

        dataset = Dataset.objects.first()
        self.assertRedirects(response, url_for('datasets.new_resource', dataset=dataset))

        self.assertIsNone(dataset.owner)
        self.assertEqual(dataset.organization, org)

    def test_create_as_org_permissions(self):
        '''It should create a dataset as an organization only for members'''
        org = OrganizationFactory()
        data = DatasetFactory.attributes()
        data['organization'] = str(org.id)
        self.login()
        response = self.post(url_for('datasets.new'), data)

        self.assert403(response)
        self.assertEqual(Dataset.objects.count(), 0)

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

    def test_delete(self):
        '''It should handle deletion from form submit and redirect on dataset page'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        response = self.post(url_for('datasets.delete', dataset=dataset))

        dataset.reload()
        self.assertRedirects(response, dataset.display_url)
        self.assertIsNotNone(dataset.deleted)

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
        '''It should render the dataset resources edit form'''
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

    def test_render_issues(self):
        '''It should render the dataset issues'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        response = self.get(url_for('datasets.issues', dataset=dataset))
        self.assert200(response)

    def test_not_found(self):
        '''It should render the dataset page'''
        response = self.get(url_for('datasets.show', dataset='not-found'))
        self.assert404(response)

    def test_recent_feed(self):
        datasets = [DatasetFactory(resources=[ResourceFactory()]) for i in range(3)]

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
        self.assertEqual(author.href, self.full_url('users.show', user=owner.id))

    def test_recent_feed_org(self):
        owner = UserFactory()
        org = OrganizationFactory()
        DatasetFactory(owner=owner, organization=org, resources=[ResourceFactory()])

        response = self.get(url_for('datasets.recent_feed'))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, org.name)
        self.assertEqual(author.href, self.full_url('organizations.show', org=org.id))

    def test_dataset_followers(self):
        '''It should render the dataset followers list page'''
        dataset = DatasetFactory()
        followers = [FollowDataset.objects.create(follower=UserFactory(), following=dataset) for _ in range(3)]

        response = self.get(url_for('datasets.followers', dataset=dataset))

        self.assert200(response)
        rendered_followers = self.get_context_variable('followers')
        self.assertEqual(len(rendered_followers), len(followers))


class MockBackend(fs.BaseBackend):
    pass


MOCK_BACKEND = '.'.join((__name__, MockBackend.__name__))


def mock_backend(func):
    return mock.patch(MOCK_BACKEND)(func)


class ResourcesTest(FrontTestCase):
    @mock_backend
    def create_app(self, mock_backend):
        app = super(ResourcesTest, self).create_app()
        app.config['FS_BACKEND'] = MOCK_BACKEND
        storages.init_app(app)
        self.backend = mock_backend.return_value
        return app

    def test_render_create_resource(self):
        '''It should render the dataset new resource page'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        response = self.get(url_for('datasets.new_resource', dataset=dataset))
        self.assert200(response)

    @mock.patch('os.path.getsize')
    def test_upload_new_resource(self, getsize):
        user = self.login()
        dataset = DatasetFactory(owner=user)
        data = {'file': (StringIO(b'aaa'), 'test.tar.gz')}
        now = datetime.now()

        getsize.return_value = 666

        response = self.post(url_for('datasets.upload_new_resource', dataset=dataset), data)
        self.assert200(response)

        self.assertTrue(response.json['success'])
        self.assertIn('filename', response.json)
        self.assertIn('sha1', response.json)
        expected_url = storages.resources.url(response.json['filename'], external=True)
        self.assertEqual(response.json['url'], expected_url)
        self.assertEqual(response.json['format'], 'tar.gz')
        self.assertEqual(response.json['size'], 666)
        filename = response.json['filename']
        self.assertIn(dataset.slug, filename)
        self.assertIn(now.strftime('%Y%m%d-%H%M%S'), filename)
        self.assertTrue(filename.endswith('test.tar.gz'))
        self.assertIn(filename, storages.resources)

    def test_render_create_community_resource(self):
        '''It should render the dataset new community resource page'''
        user = self.login()
        dataset = DatasetFactory(owner=user)
        response = self.get(url_for('datasets.new_community_resource', dataset=dataset))
        self.assert200(response)

    @mock.patch('os.path.getsize')
    def test_upload_new_community_resource(self, getsize):
        self.login()
        dataset = DatasetFactory(owner=UserFactory())
        data = {'file': (StringIO(b'aaa'), 'test.txt')}
        now = datetime.now()

        getsize.return_value = 666

        response = self.post(url_for('datasets.upload_new_community_resource', dataset=dataset), data)
        self.assert200(response)

        self.assertTrue(response.json['success'])
        self.assertIn('filename', response.json)
        self.assertIn('url', response.json)
        self.assertIn('sha1', response.json)
        self.assertEqual(response.json['format'], 'txt')
        self.assertEqual(response.json['size'], 666)
        filename = response.json['filename']
        self.assertIn('community', filename)
        self.assertIn(dataset.slug, filename)
        self.assertIn(now.strftime('%Y%m%d-%H%M%S'), filename)
        self.assertTrue(filename.endswith('test.txt'))

    def test_render_edit_resource(self):
        '''It should render the dataset new resource page'''
        user = self.login()
        resource = ResourceFactory()
        dataset = DatasetFactory(owner=user, resources=[resource])
        response = self.get(url_for('datasets.edit_resource', dataset=dataset, resource=resource.id))
        self.assert200(response)

    def test_render_edit_community_resource(self):
        '''It should render the dataset new community resource page'''
        user = self.login()
        resource = ResourceFactory(owner=user)
        dataset = DatasetFactory(owner=UserFactory(), community_resources=[resource])
        response = self.get(url_for('datasets.edit_community_resource', dataset=dataset, resource=resource.id))
        self.assert200(response)

    def test_delete_resource(self):
        '''It should handle deletion from form submit and redirect on dataset page'''
        user = self.login()
        resource = ResourceFactory()
        dataset = DatasetFactory(owner=user, resources=[resource, ResourceFactory()])
        response = self.post(url_for('datasets.delete_resource', dataset=dataset, resource=resource.id))

        dataset.reload()
        self.assertRedirects(response, dataset.display_url)
        self.assertIsNone(dataset.deleted)
        self.assertEqual(len(dataset.resources), 1)
        self.assertNotEqual(dataset.resources[0].id, resource.id)

    def test_delete_community_resource(self):
        '''It should handle deletion from form submit and redirect on dataset page'''
        user = self.login()
        resource = ResourceFactory(owner=user)
        dataset = DatasetFactory(
            owner=UserFactory(),
            resources=[ResourceFactory()],
            community_resources=[resource, ResourceFactory()]
        )
        response = self.post(url_for('datasets.delete_community_resource', dataset=dataset, resource=resource.id))

        dataset.reload()
        self.assertRedirects(response, dataset.display_url)
        self.assertIsNone(dataset.deleted)
        self.assertEqual(len(dataset.community_resources), 1)
        self.assertNotEqual(dataset.community_resources[0].id, resource.id)
