# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from flask import url_for

from udata.frontend.markdown import mdstrip

from . import APITestCase
from udata.core.dataset.factories import DatasetFactory
from udata.core.user.factories import UserFactory
from udata.core.organization.factories import OrganizationFactory


class OEmbedsDatasetAPITest(APITestCase):

    def test_oembeds_dataset_api_get(self):
        '''It should fetch a dataset in the oembed format.'''
        with self.autoindex():
            dataset = DatasetFactory()

        url = url_for('api.oembeds',
                      references='dataset-{id}'.format(id=dataset.id))
        response = self.get(url)
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
        self.assertIn(mdstrip(dataset.description, 110), data['html'])

    def test_oembeds_dataset_api_get_with_organization(self):
        '''It should fetch a dataset in the oembed format with org.'''
        with self.autoindex():
            organization = OrganizationFactory()
            dataset = DatasetFactory(organization=organization)

        url = url_for('api.oembeds',
                      references='dataset-{id}'.format(id=dataset.id))
        response = self.get(url)
        self.assert200(response)
        data = json.loads(response.data)[0]
        self.assertIn(organization.name, data['html'])
        self.assertIn(organization.external_url, data['html'])

    def test_oembeds_dataset_api_get_without_references(self):
        '''It should fail at fetching an oembed without a dataset.'''
        response = self.get(url_for('api.oembeds'))
        self.assert400(response)
        data = json.loads(response.data)
        self.assertIn('references', data['errors'])

    def test_oembeds_dataset_api_get_without_good_id(self):
        '''It should fail at fetching an oembed without a good id.'''
        response = self.get(url_for('api.oembeds', references='123456789'))
        self.assert400(response)
        self.assertEqual(json.loads(response.data)['message'], 'Invalid ID.')

    def test_oembeds_dataset_api_get_without_good_item(self):
        '''It should fail at fetching an oembed with a wrong item.'''
        with self.autoindex():
            user = UserFactory()

        url = url_for('api.oembeds', references='user-{id}'.format(id=user.id))
        response = self.get(url)
        self.assert400(response)
        self.assertEqual(json.loads(response.data)['message'],
                         'Invalid object type.')

    def test_oembeds_dataset_api_get_without_valid_id(self):
        '''It should fail at fetching an oembed without a valid id.'''
        url = url_for('api.oembeds', references='dataset-123456789')
        response = self.get(url)
        self.assert400(response)
        self.assertEqual(json.loads(response.data)['message'],
                         'Unknown dataset ID.')
