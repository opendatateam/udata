# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from flask import url_for

from . import APITestCase
from ..factories import DatasetFactory, OrganizationFactory, UserFactory


class OEmbedsDatasetAPITest(APITestCase):

    def test_oembeds_dataset_api_get(self):
        '''It should fetch a dataset in the oembed format.'''
        with self.autoindex():
            dataset = DatasetFactory()

        response = self.get(
            url_for('api.oembeds',
                    references='dataset-{id}'.format(id=dataset.id)))
        self.assert200(response)
        data = json.loads(response.data)[0]
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

    def test_oembeds_dataset_api_get_with_organization(self):
        '''It should fetch a dataset in the oembed format with org.'''
        with self.autoindex():
            organization = OrganizationFactory()
            dataset = DatasetFactory(organization=organization)

        response = self.get(
            url_for('api.oembeds',
                    references='dataset-{id}'.format(id=dataset.id)))
        self.assert200(response)
        data = json.loads(response.data)[0]
        self.assertNotIn('placeholders/default.png', data['html'])
        self.assertIn(organization.name, data['html'])
        self.assertIn(organization.external_url, data['html'])

    def test_oembeds_dataset_api_get_without_references(self):
        '''It should fail at fetching an oembed without a dataset.'''
        response = self.get(url_for('api.oembeds'))
        self.assert400(response)
        data = json.loads(response.data)
        self.assertEqual(
            data['message']['references'],
            ("(References of the resources to embed.)  "
             "Missing required parameter in the query string"))

    def test_oembeds_dataset_api_get_without_good_id(self):
        '''It should fail at fetching an oembed without a good id.'''
        response = self.get(url_for('api.oembeds', references='123456789'))
        self.assert400(response)
        self.assertEqual(json.loads(response.data)['message'], 'Invalid ID.')

    def test_oembeds_dataset_api_get_without_good_item(self):
        '''It should fail at fetching an oembed with a wrong item.'''
        with self.autoindex():
            user = UserFactory()

        response = self.get(
            url_for('api.oembeds', references='user-{id}'.format(id=user.id)))
        self.assert400(response)
        self.assertEqual(json.loads(response.data)['message'],
                         'Invalid object type.')

    def test_oembeds_dataset_api_get_without_valid_id(self):
        '''It should fail at fetching an oembed without a valid id.'''
        response = self.get(
            url_for('api.oembeds', references='dataset-123456789'))
        self.assert400(response)
        self.assertEqual(json.loads(response.data)['message'],
                         'Unknown dataset ID.')
