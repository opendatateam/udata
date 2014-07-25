# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from flask import url_for

from udata.models import Dataset

from . import APITestCase
from ..factories import DatasetFactory, ResourceFactory, faker


class DatasetAPITest(APITestCase):
    def test_dataset_api_list(self):
        '''It should fetch a dataset list from the API'''
        with self.autoindex():
            datasets = [DatasetFactory(resources=[ResourceFactory()]) for i in range(3)]

        response = self.get(url_for('api.datasets'))
        self.assert200(response)
        self.assertEqual(len(response.json['data']), len(datasets))

    def test_dataset_api_get(self):
        '''It should fetch a dataset from the API'''
        with self.autoindex():
            resources = [ResourceFactory() for _ in range(3)]
            dataset = DatasetFactory(resources=resources)

        response = self.get(url_for('api.dataset', slug=dataset.slug))
        self.assert200(response)
        data = json.loads(response.data)
        self.assertEqual(len(data['resources']), len(resources))

    def test_dataset_api_create(self):
        '''It should create a dataset from the API'''
        data = DatasetFactory.attributes()
        with self.api_user():
            response = self.post(url_for('api.datasets'), data)
        self.assertStatus(response, 201)
        self.assertEqual(Dataset.objects.count(), 1)

    def test_dataset_api_update(self):
        '''It should update a dataset from the API'''
        dataset = DatasetFactory()
        data = dataset.to_dict()
        data['description'] = 'new description'
        with self.api_user():
            response = self.put(url_for('api.dataset', slug=dataset.slug), data)
        self.assert200(response)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertEqual(Dataset.objects.first().description, 'new description')

    def test_dataset_api_delete(self):
        '''It should delete a dataset from the API'''
        dataset = DatasetFactory()
        with self.api_user():
            response = self.delete(url_for('api.dataset', slug=dataset.slug))
        self.assertStatus(response, 204)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertIsNotNone(Dataset.objects[0].deleted)

    def test_dataset_api_feature(self):
        '''It should mark the dataset featured on POST'''
        dataset = DatasetFactory(featured=False)

        with self.api_user():
            response = self.post(url_for('api.dataset_featured', slug=dataset.slug))

        self.assert200(response)

        dataset.reload()
        self.assertTrue(dataset.featured)

    def test_dataset_api_feature_already(self):
        '''It shouldn't do anything to feature an already featured dataset'''
        dataset = DatasetFactory(featured=True)

        with self.api_user():
            response = self.post(url_for('api.dataset_featured', slug=dataset.slug))

        self.assert200(response)

        dataset.reload()
        self.assertTrue(dataset.featured)

    def test_dataset_api_unfeature(self):
        '''It should unmark the dataset featured on POST'''
        dataset = DatasetFactory(featured=True)

        with self.api_user():
            response = self.delete(url_for('api.dataset_featured', slug=dataset.slug))

        self.assert200(response)

        dataset.reload()
        self.assertFalse(dataset.featured)

    def test_dataset_api_unfeature_already(self):
        '''It shouldn't do anything to unfeature a not featured dataset'''
        dataset = DatasetFactory(featured=False)

        with self.api_user():
            response = self.delete(url_for('api.dataset_featured', slug=dataset.slug))

        self.assert200(response)

        dataset.reload()
        self.assertFalse(dataset.featured)


class DatasetResourceAPITest(APITestCase):
    def setUp(self):
        self.dataset = DatasetFactory()
        self.login()

    def test_create(self):
        data = ResourceFactory.attributes()
        with self.api_user():
            response = self.post(url_for('api.resources', slug=self.dataset.slug), data)
        self.assertStatus(response, 201)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 1)

    def test_update(self):
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
        }
        with self.api_user():
            response = self.put(url_for('api.resource', slug=self.dataset.slug, rid=str(resource.id)), data)
        self.assert200(response)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 1)
        updated = self.dataset.resources[0]
        self.assertEqual(updated.title, data['title'])
        self.assertEqual(updated.description, data['description'])
        self.assertEqual(updated.url, data['url'])

    def test_update_404(self):
        data = {
            'title': faker.sentence(),
            'description': faker.text(),
            'url': faker.url(),
        }
        with self.api_user():
            response = self.put(url_for('api.resource', slug=self.dataset.slug, rid=str(ResourceFactory().id)), data)
        self.assert404(response)

    def test_delete(self):
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        with self.api_user():
            response = self.delete(url_for('api.resource', slug=self.dataset.slug, rid=str(resource.id)))
        self.assertStatus(response, 204)
        self.dataset.reload()
        self.assertEqual(len(self.dataset.resources), 0)

    def test_delete_404(self):
        with self.api_user():
            response = self.delete(url_for('api.resource', slug=self.dataset.slug, rid=str(ResourceFactory().id)))
        self.assert404(response)
