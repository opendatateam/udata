# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import url_for

from udata.models import Member
from udata.core.spatial.factories import GeoZoneFactory, SpatialCoverageFactory
from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.tests.frontend import FrontTestCase
from udata.settings import Testing


def create_geozones_fixtures():
    paca = GeoZoneFactory(
        id='REG93@1970-01-09', level='fr/region',
        name='Provence Alpes Côtes dAzur')
    bdr = GeoZoneFactory(
        id='DEP13@1860-07-01', level='fr/departement', parents=[paca.id],
        name='Bouches-du-Rhône', code='13', population=1993177, area=0)
    arles = GeoZoneFactory(
        id='COM13004@1942-01-01', level='fr/commune', parents=[bdr.id],
        name='Arles', code='13004', keys={'postal': '13200'},
        population=52439, area=0)
    return paca, bdr, arles


def create_old_new_regions_fixtures():
    lr = GeoZoneFactory(
        id='REG91@1970-01-09', level='fr/region',
        name='Languedoc-Rousillon',
        validity={'start': '1956-01-01', 'end': '2015-12-31'},
        population=2700266)
    occitanie = GeoZoneFactory(
        id='REG76@2016-01-01', level='fr/region',
        name='Languedoc-Rousillon et Midi-Pyrénées',
        ancestors=['REG91@1970-01-09'],
        validity={'start': '2016-01-01', 'end': '9999-12-31'},
        population=5573000)
    return lr, occitanie


class TerritoriesSettings(Testing):
    ACTIVATE_TERRITORIES = True
    HANDLED_LEVELS = ('fr/commune', 'fr/departement', 'fr/region', 'country')


class TerritoriesTest(FrontTestCase):
    settings = TerritoriesSettings

    def setUp(self):
        super(TerritoriesTest, self).setUp()
        self.paca, self.bdr, self.arles = create_geozones_fixtures()

    def test_towns_with_default_base_datasets(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.arles))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(self.arles.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)
        self.assertIn(self.bdr.name, data)

    def test_counties_with_default_base_datasets(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.bdr))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(self.bdr.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)

    def test_regions_with_default_base_datasets(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.paca))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(self.paca.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)

    def test_towns_with_other_datasets(self):
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
        self.assertIn(self.arles.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        for dataset in other_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)

    def test_counties_with_other_datasets(self):
        with self.autoindex():
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.bdr.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.bdr))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(self.bdr.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        for dataset in other_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)

    def test_regions_with_other_datasets(self):
        with self.autoindex():
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.paca.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.paca))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(self.paca.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        for dataset in other_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)

    def test_towns_with_other_datasets_logged_in(self):
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
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('If you want your datasets to appear in that list', data)

    def test_counties_with_other_datasets_logged_in(self):
        self.login()
        with self.autoindex():
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.bdr.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.bdr))
        self.assert200(response)
        data = response.data.decode('utf-8')
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('If you want your datasets to appear in that list', data)

    def test_regions_with_other_datasets_logged_in(self):
        self.login()
        with self.autoindex():
            organization = OrganizationFactory()
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.paca.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.paca))
        self.assert200(response)
        data = response.data.decode('utf-8')
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('If you want your datasets to appear in that list', data)

    def test_towns_with_other_datasets_and_pertinent_ones(self):
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
        self.assertIn(self.arles.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        for dataset in other_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertTrue(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('Some of your datasets have an exact match!', data)

    def test_counties_with_other_datasets_and_pertinent_ones(self):
        user = self.login()
        with self.autoindex():
            member = Member(user=user, role='admin')
            organization = OrganizationFactory(members=[member])
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.bdr.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.bdr))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(self.bdr.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        for dataset in other_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertTrue(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('Some of your datasets have an exact match!', data)

    def test_regions_with_other_datasets_and_pertinent_ones(self):
        user = self.login()
        with self.autoindex():
            member = Member(user=user, role='admin')
            organization = OrganizationFactory(members=[member])
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.paca.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.paca))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(self.paca.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        for dataset in other_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertTrue(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
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
        self.assertIn(self.arles.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        territory_datasets = self.get_context_variable('territory_datasets')
        self.assertEqual(len(territory_datasets), 3)
        for dataset in territory_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertNotIn('dataset-item--cta', data)

    def test_with_county_datasets(self):
        with self.autoindex():
            organization = OrganizationFactory(zone=self.bdr.id)
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.bdr.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.bdr))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(self.bdr.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        territory_datasets = self.get_context_variable('territory_datasets')
        self.assertEqual(len(territory_datasets), 3)
        for dataset in territory_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertNotIn('dataset-item--cta', data)

    def test_with_region_datasets(self):
        with self.autoindex():
            organization = OrganizationFactory(zone=self.paca.id)
            for _ in range(3):
                VisibleDatasetFactory(
                    organization=organization,
                    spatial=SpatialCoverageFactory(zones=[self.paca.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.paca))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(self.paca.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        territory_datasets = self.get_context_variable('territory_datasets')
        self.assertEqual(len(territory_datasets), 3)
        for dataset in territory_datasets:
            self.assertIn(
                '<div data-udata-dataset-id="{dataset.id}"'.format(
                    dataset=dataset),
                data)
        self.assertFalse(self.get_context_variable('has_pertinent_datasets'))
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertNotIn('dataset-item--cta', data)

    def test_with_old_region_datasets(self):
        lr, occitanie = create_old_new_regions_fixtures()
        with self.autoindex():
            for region in [lr, occitanie]:
                organization = OrganizationFactory(zone=region.id)
                VisibleDatasetFactory.build_batch(
                    3, organization=organization,
                    spatial=SpatialCoverageFactory(zones=[region.id]))
        response = self.client.get(
            url_for('territories.territory', territory=occitanie))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(occitanie.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        territory_datasets = self.get_context_variable('territory_datasets')
        self.assertEqual(len(territory_datasets), 3)
        territory_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(territory_datasets), 3)
