# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from flask import url_for

from . import APITestCase
from ..factories import DatasetFactory, OrganizationFactory, UserFactory


class OEmbedDatasetAPITest(APITestCase):

    def test_oembed_dataset_api_get(self):
        '''It should fetch a dataset in the oembed format.'''
        with self.autoindex():
            dataset = DatasetFactory()

        dataset_url = url_for(
            'api.dataset', dataset=dataset.id, _external=True)
        response = self.get(url_for('api.oembed', **{'url': dataset_url}))
        self.assert200(response)
        data = json.loads(response.data)
        self.assertIn('html', data)
        self.assertIn('width', data)
        self.assertIn('maxwidth', data)
        self.assertIn('height', data)
        self.assertIn('maxheight', data)
        self.assertTrue(data['type'], 'rich')
        self.assertTrue(data['version'], '1.0')
        self.assertIn(dataset.title, data['html'])
        self.assertIn(dataset.external_url, data['html'])
        self.assertIn('placeholders/default.png', data['html'])
        # Because we use mdstrip for the description.
        self.assertIn(dataset.description[:90], data['html'])

    def test_oembed_dataset_api_get_with_organization(self):
        '''It should fetch a dataset in the oembed format with org.'''
        with self.autoindex():
            organization = OrganizationFactory()
            dataset = DatasetFactory(organization=organization)

        dataset_url = url_for(
            'api.dataset', dataset=dataset.id, _external=True)
        response = self.get(url_for('api.oembed', **{'url': dataset_url}))
        self.assert200(response)
        data = json.loads(response.data)
        self.assertNotIn('placeholders/default.png', data['html'])
        self.assertIn(organization.name, data['html'])
        self.assertIn(organization.external_url, data['html'])

    def test_oembed_dataset_api_get_without_url(self):
        '''It should fail at fetching an oembed without a dataset.'''
        response = self.get(url_for('api.oembed'))
        self.assert400(response)
        data = json.loads(response.data)
        self.assertEqual(
            data['message']['url'],
            ("(URL of the resource to embed.)  "
             "Missing required parameter in the query string"))

    def test_oembed_dataset_api_get_without_good_url(self):
        '''It should fail at fetching an oembed without a wrong url.'''
        with self.autoindex():
            dataset = DatasetFactory()

        dataset_url = url_for(
            'datasets.show', dataset=dataset.id, _external=True)
        response = self.get(url_for('api.oembed', **{'url': dataset_url}))
        self.assert400(response)
        self.assertEqual(json.loads(response.data)['message'], 'Invalid URL.')

    def test_oembed_dataset_api_get_without_good_item(self):
        '''It should fail at fetching an oembed without a wrong item.'''
        with self.autoindex():
            user = UserFactory()

        user_url = url_for('api.user', user=user.id, _external=True)
        response = self.get(url_for('api.oembed', **{'url': user_url}))
        self.assert400(response)
        self.assertEqual(json.loads(response.data)['message'],
                         'Invalid object type.')

    def test_oembed_dataset_api_get_without_valid_id(self):
        '''It should fail at fetching an oembed without a valid id.'''
        dataset_url = url_for(
            'api.dataset', dataset='incorrect-id', _external=True)
        response = self.get(url_for('api.oembed', **{'url': dataset_url}))
        self.assert400(response)
        self.assertEqual(json.loads(response.data)['message'], 'Incorrect ID.')

    def test_oembed_dataset_api_get_without_existing_id(self):
        '''It should fail at fetching an oembed without a existing id.'''
        dataset_id = '5661724a4a7bd1d4ab4c7956'  # Inexisting ID.
        dataset_url = url_for(
            'api.dataset', dataset=dataset_id, _external=True)
        response = self.get(url_for('api.oembed', **{'url': dataset_url}))
        self.assert400(response)
        self.assertEqual(json.loads(response.data)['message'], 'Incorrect ID.')
