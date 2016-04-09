# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Member
from udata.tests.factories import (
    GeoZoneFactory, VisibleDatasetFactory, OrganizationFactory
)
from udata.core.spatial.tests.factories import SpatialCoverageFactory
from udata.tests.frontend import FrontTestCase
from udata.settings import Testing


def create_geozones_fixtures():
    bdr = GeoZoneFactory(
        id='fr/county/13', level='fr/county', name='Bouches-du-Rhône')
    arles = GeoZoneFactory(
        id='fr/town/13004', level='fr/town', parents=[bdr.id],
        name='Arles', code='13004', population=52439)
    return bdr, arles


class TerritoriesSettings(Testing):
    ACTIVATE_TERRITORIES = True


class TerritoriesTest(FrontTestCase):
    settings = TerritoriesSettings

    def setUp(self):
        self.bdr, self.arles = create_geozones_fixtures()
        super(TerritoriesTest, self).setUp()

    def test_with_detault_territory_datasets(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.arles))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn('Arles', data)
        territory_datasets = self.get_context_variable('territory_datasets')
        self.assertEqual(len(territory_datasets), 0)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('town_datasets'), [])
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)
        self.assertIn(self.bdr.name, data)

    def test_with_other_datasets(self):
        with self.autoindex():
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.arles.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.arles))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn('Arles', data)
        territory_datasets = self.get_context_variable('territory_datasets')
        self.assertEqual(len(territory_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        for dataset in other_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('town_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)

    def test_with_other_datasets_logged_in(self):
        self.login()
        with self.autoindex():
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.arles.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.arles))
        self.assert200(response)
        data = response.data.decode('utf-8')
        territory_datasets = self.get_context_variable('territory_datasets')
        self.assertEqual(len(territory_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('town_datasets'), [])
        self.assertIn('If you want your datasets to appear in that list', data)

    def test_with_other_datasets_and_pertinent_ones(self):
        user = self.login()
        with self.autoindex():
            member = Member(user=user, role='admin')
            organization = OrganizationFactory(members=[member])
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.arles.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.arles))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn('Arles', data)
        territory_datasets = self.get_context_variable('territory_datasets')
        self.assertEqual(len(territory_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        for dataset in other_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertTrue(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('town_datasets'), [])
        self.assertIn('Some of your datasets have an exact match!', data)

    def test_with_town_datasets(self):
        with self.autoindex():
            organization = OrganizationFactory(zone=self.arles.id)
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.arles.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.arles))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn('Arles', data)
        territory_datasets = self.get_context_variable('territory_datasets')
        self.assertEqual(len(territory_datasets), 0)
        town_datasets = self.get_context_variable('town_datasets')
        self.assertEqual(len(town_datasets), 3)
        for dataset in town_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertNotIn('dataset-item--cta', data)
