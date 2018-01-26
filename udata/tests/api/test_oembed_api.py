# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import json

from flask import url_for

from udata.core.dataset.factories import DatasetFactory
from udata.core.spatial.factories import GeoZoneFactory
from udata.core.user.factories import UserFactory
from udata.core.organization.factories import OrganizationFactory
from udata.features.territories.models import (
    TerritoryDataset, TERRITORY_DATASETS
)
from udata.frontend.markdown import mdstrip
from udata.settings import Testing
from udata.utils import faker

from . import APITestCase


def territory_dataset_factory():
    org = OrganizationFactory()

    class TestDataset(TerritoryDataset):
        order = 1
        id = faker.word()
        title = faker.sentence()
        organization_id = str(org.id)
        description = faker.paragraph()
        temporal_coverage = {'start': 2007, 'end': 2012}
        url_template = 'http://somehere.com/{code}'

    return TestDataset


class OEmbedSettings(Testing):
    ACTIVATE_TERRITORIES = True


class OEmbedsDatasetAPITest(APITestCase):
    modules = ['core.organization', 'features.territories', 'core.dataset']
    settings = OEmbedSettings

    def setUp(self):
        self.territory_datasets_backup = {
            k: copy.deepcopy(v) for k, v in TERRITORY_DATASETS.items()
        }

    def tearDown(self):
        super(OEmbedsDatasetAPITest, self).tearDown()
        TERRITORY_DATASETS.update(self.territory_datasets_backup)

    def test_oembeds_dataset_api_get(self):
        '''It should fetch a dataset in the oembed format.'''
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

    def test_oembeds_api_for_territory(self):
        '''It should fetch a territory in the oembed format.'''
        country = faker.country_code().lower()
        level = 'commune'
        zone = GeoZoneFactory(level='{0}:{1}'.format(country, level))
        TestDataset = territory_dataset_factory()
        TERRITORY_DATASETS[level][TestDataset.id] = TestDataset
        reference = 'territory-{0}:{1}'.format(zone.id, TestDataset.id)
        url = url_for('api.oembeds', references=reference)
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
        self.assertIn(zone.name, data['html'])
        self.assertIn('placeholders/default.png', data['html'])

    def test_oembeds_api_for_territory_resolve_geoid(self):
        '''It should fetch a territory from a geoid in the oembed format.'''
        country = faker.country_code().lower()
        level = 'commune'
        zone = GeoZoneFactory(level='{0}:{1}'.format(country, level))
        TestDataset = territory_dataset_factory()
        TERRITORY_DATASETS[level][TestDataset.id] = TestDataset
        geoid = '{0.level}:{0.code}@latest'.format(zone)
        reference = 'territory-{0}:{1}'.format(geoid, TestDataset.id)

        url = url_for('api.oembeds', references=reference)
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
        self.assertIn(zone.name, data['html'])
        self.assertIn('placeholders/default.png', data['html'])

    def test_oembeds_api_for_territory_bad_id(self):
        '''Should raise 400 on bad territory ID'''
        url = url_for('api.oembeds', references='territory-xyz')
        response = self.get(url)
        self.assert400(response)
        self.assertEqual(response.json['message'], 'Invalid territory ID.')

    def test_oembeds_api_for_territory_zone_not_found(self):
        '''Should raise 400 on unknown zone ID'''
        url = url_for('api.oembeds',
                      references='territory-fr:commune:13004@1970-01-01:xyz')
        response = self.get(url)
        self.assert400(response)
        self.assertEqual(response.json['message'],
                         'Unknown territory identifier.')

    def test_oembeds_api_for_territory_level_not_registered(self):
        '''Should raise 400 on unregistered territory level'''
        country = faker.country_code().lower()
        level = 'commune'
        zone = GeoZoneFactory(level='{0}:{1}'.format(country, level))
        TestDataset = territory_dataset_factory()
        del TERRITORY_DATASETS[level]
        reference = 'territory-{0}:{1}'.format(zone.id, TestDataset.id)
        url = url_for('api.oembeds', references=reference)
        response = self.get(url)
        self.assert400(response)
        self.assertEqual(response.json['message'],
                         'Unknown kind of territory.')

    def test_oembeds_api_for_territory_dataset_not_registered(self):
        '''Should raise 400 on unregistered territory dataset'''
        country = faker.country_code().lower()
        level = 'commune'
        zone = GeoZoneFactory(level='{0}:{1}'.format(country, level))
        TestDataset = territory_dataset_factory()
        TERRITORY_DATASETS[level] = {}
        reference = 'territory-{0}:{1}'.format(zone.id, TestDataset.id)
        url = url_for('api.oembeds', references=reference)
        response = self.get(url)
        self.assert400(response)
        self.assertEqual(response.json['message'],
                         'Unknown territory dataset id.')
