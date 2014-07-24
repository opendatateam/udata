# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Reuse

from . import APITestCase
from ..factories import ReuseFactory, DatasetFactory


class ReuseAPITest(APITestCase):
    def test_reuse_api_list(self):
        '''It should fetch a reuse list from the API'''
        with self.autoindex():
            reuses = [ReuseFactory(datasets=[DatasetFactory()]) for i in range(3)]

        response = self.get(url_for('api.reuses'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(reuses))

    def test_reuse_api_get(self):
        '''It should fetch a reuse from the API'''
        reuse = ReuseFactory()
        response = self.get(url_for('api.reuse', slug=reuse.slug))
        self.assert200(response)

    def test_reuse_api_create(self):
        '''It should create a reuse from the API'''
        data = ReuseFactory.attributes()
        self.login()
        response = self.post(url_for('api.reuses'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Reuse.objects.count(), 1)

    def test_reuse_api_update(self):
        '''It should update a reuse from the API'''
        reuse = ReuseFactory()
        data = reuse.to_dict()
        data['description'] = 'new description'
        self.login()
        response = self.put(url_for('api.reuse', slug=reuse.slug), data)
        self.assert200(response)
        self.assertEqual(Reuse.objects.count(), 1)
        self.assertEqual(Reuse.objects.first().description, 'new description')

    def test_reuse_api_delete(self):
        '''It should delete a reuse from the API'''
        reuse = ReuseFactory()
        with self.api_user():
            response = self.delete(url_for('api.reuse', slug=reuse.slug))
        self.assertStatus(response, 204)
        self.assertEqual(Reuse.objects.count(), 1)
        self.assertIsNotNone(Reuse.objects[0].deleted)

    def test_reuse_api_feature(self):
        '''It should mark the reuse featured on POST'''
        reuse = ReuseFactory(featured=False)

        with self.api_user():
            response = self.post(url_for('api.reuse_featured', slug=reuse.slug))
        self.assert200(response)

        reuse.reload()
        self.assertTrue(reuse.featured)

    def test_reuse_api_feature_already(self):
        '''It shouldn't do anything to feature an already featured reuse'''
        reuse = ReuseFactory(featured=True)

        with self.api_user():
            response = self.post(url_for('api.reuse_featured', slug=reuse.slug))
        self.assert200(response)

        reuse.reload()
        self.assertTrue(reuse.featured)

    def test_reuse_api_unfeature(self):
        '''It should mark the reuse featured on POST'''
        reuse = ReuseFactory(featured=True)

        with self.api_user():
            response = self.delete(url_for('api.reuse_featured', slug=reuse.slug))
        self.assert200(response)

        reuse.reload()
        self.assertFalse(reuse.featured)

    def test_reuse_api_unfeature_already(self):
        '''It shouldn't do anything to unfeature a not featured reuse'''
        reuse = ReuseFactory(featured=False)

        with self.api_user():
            response = self.delete(url_for('api.reuse_featured', slug=reuse.slug))
        self.assert200(response)

        reuse.reload()
        self.assertFalse(reuse.featured)
