# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.core.dataset.factories import DatasetFactory, ResourceFactory
from udata.core.reuse.factories import ReuseFactory
from udata.utils import faker

from . import APITestCase


class TagsAPITest(APITestCase):
    def test_suggest_tags_api(self):
        '''It should suggest tags'''
        with self.autoindex():
            for i in range(3):
                tags = [faker.word(), faker.word(), 'test',
                        'test-{0}'.format(i)]
                ReuseFactory(tags=tags, datasets=[DatasetFactory()])
                DatasetFactory(tags=tags, resources=[ResourceFactory()])

        response = self.get(url_for('api.suggest_tags'),
                            qs={'q': 'tes', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)
        self.assertEqual(response.json[0]['text'], 'test')

        for suggestion in response.json:
            self.assertIn('text', suggestion)
            self.assertIn('score', suggestion)
            self.assertTrue(suggestion['text'].startswith('test'))
    
    def test_suggest_tags_api_with_unicode(self):
        '''It should suggest tags'''
        with self.autoindex():
            for i in range(3):
                tags = [faker.word(), faker.word(), 'testé',
                        'testé-{0}'.format(i)]
                ReuseFactory(tags=tags, visible=True)
                DatasetFactory(tags=tags, visible=True)

        response = self.get(url_for('api.suggest_tags'),
                            qs={'q': 'testé', 'size': '5'})
        self.assert200(response)

        self.assertLessEqual(len(response.json), 5)
        self.assertGreater(len(response.json), 1)
        self.assertEqual(response.json[0]['text'], 'teste')

        for suggestion in response.json:
            self.assertIn('text', suggestion)
            self.assertIn('score', suggestion)
            self.assertTrue(suggestion['text'].startswith('teste'))

    def test_suggest_tags_api_no_match(self):
        '''It should not provide tag suggestion if no match'''
        with self.autoindex():
            for i in range(3):
                tags = ['aaaa', 'aaaa-{0}'.format(i)]
                ReuseFactory(tags=tags, datasets=[DatasetFactory()])
                DatasetFactory(tags=tags, resources=[ResourceFactory()])

        response = self.get(url_for('api.suggest_tags'),
                            qs={'q': 'bbbb', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)

    def test_suggest_tags_api_empty(self):
        '''It should not provide tag suggestion if no data'''
        self.init_search()
        response = self.get(url_for('api.suggest_tags'),
                            qs={'q': 'bbbb', 'size': '5'})
        self.assert200(response)
        self.assertEqual(len(response.json), 0)
