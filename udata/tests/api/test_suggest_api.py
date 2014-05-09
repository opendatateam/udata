# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from . import APITestCase
from ..factories import ReuseFactory, DatasetFactory, ResourceFactory, OrganizationFactory, UserFactory, faker


class SuggestAPITest(APITestCase):
    def test_suggest_tags_api(self):
        '''It should suggest tags'''
        with self.autoindex():
            for i in range(3):
                tags = [faker.word(), faker.word(), 'test', 'test-{0}'.format(i)]
                ReuseFactory(tags=tags)
                DatasetFactory(tags=tags)

        response = self.get(url_for('api.suggest_tags'), qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)
        self.assertEqual(response.json[0]['text'], 'test')

        for suggestion in response.json:
            self.assertIn('text', suggestion)
            self.assertIn('score', suggestion)
            self.assertTrue(suggestion['text'].startswith('test'))

    def test_suggest_tags_api_empty(self):
        '''It should not provide tag suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                tags = ['aaaa', 'aaaa-{0}'.format(i)]
                ReuseFactory(tags=tags)
                DatasetFactory(tags=tags)

        response = self.get(url_for('api.suggest_tags'), qs={'q': 'bbbb', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_formats_api(self):
        '''It should suggest formats'''
        with self.autoindex():
            for i in range(3):
                tags = [faker.word(), faker.word(), 'test', 'test-{0}'.format(i)]
                ReuseFactory(tags=tags)
            DatasetFactory(resources=[
                ResourceFactory(format=f) for f in (faker.word(), faker.word(), 'test', 'test-1')
            ])

        response = self.get(url_for('api.suggest_formats'), qs={'q': 'test', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)
        self.assertEqual(response.json[0]['text'], 'test')

        for suggestion in response.json:
            self.assertIn('text', suggestion)
            self.assertIn('score', suggestion)
            self.assertTrue(suggestion['text'].startswith('test'))

    def test_suggest_format_api_empty(self):
        '''It should not provide format suggestion if no match'''
        with self.autoindex():
            DatasetFactory(resources=[
                ResourceFactory(format=faker.word()) for _ in range(3)
            ])

        response = self.get(url_for('api.suggest_formats'), qs={'q': 'test', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_datasets_api(self):
        '''It should suggest datasets'''
        with self.autoindex():
            for i in range(4):
                DatasetFactory(title='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_datasets'), qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['title'].startswith('test'))

    def test_suggest_datasets_api_empty(self):
        '''It should not provide dataset suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                DatasetFactory()

        response = self.get(url_for('api.suggest_datasets'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_users_api_first_name(self):
        '''It should suggest users'''
        with self.autoindex():
            for i in range(4):
                UserFactory(first_name='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_users'), qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('fullname', suggestion)
            self.assertIn('avatar_url', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('test', suggestion['fullname'])

    def test_suggest_users_api_last_name(self):
        '''It should suggest users'''
        with self.autoindex():
            for i in range(4):
                UserFactory(last_name='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_users'), qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('fullname', suggestion)
            self.assertIn('avatar_url', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('test', suggestion['fullname'])

    def test_suggest_users_api_empty(self):
        '''It should not provide user suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                UserFactory()

        response = self.get(url_for('api.suggest_users'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_organizations_api(self):
        '''It should suggest organizations'''
        with self.autoindex():
            for i in range(4):
                OrganizationFactory(name='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_orgs'), qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['name'].startswith('test'))

    def test_suggest_organizations_api_empty(self):
        '''It should not provide organization suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                OrganizationFactory()

        response = self.get(url_for('api.suggest_orgs'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_reuses_api(self):
        '''It should suggest reuses'''
        with self.autoindex():
            for i in range(4):
                ReuseFactory(title='test-{0}'.format(i) if i % 2 else faker.word())

        response = self.get(url_for('api.suggest_reuses'), qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)

        for suggestion in response.json:
            self.assertIn('id', suggestion)
            self.assertIn('slug', suggestion)
            self.assertIn('title', suggestion)
            self.assertIn('score', suggestion)
            self.assertIn('image_url', suggestion)
            self.assertTrue(suggestion['title'].startswith('test'))

    def test_suggest_reuses_api_empty(self):
        '''It should not provide reuse suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                ReuseFactory()

        response = self.get(url_for('api.suggest_reuses'), qs={'q': 'xxxxxx', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)
