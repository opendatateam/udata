import pytest
from flask import url_for

from udata.core.dataset.factories import VisibleDatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.spatial.factories import SpatialCoverageFactory
from udata.models import Member
from udata.tests.features.territories import (
    create_geozones_fixtures, create_old_new_regions_fixtures,
    TerritoriesSettings
)
from udata_front.tests.frontend import GouvfrFrontTestCase


class GouvFrTerritoriesSettings(TerritoriesSettings):
    TEST_WITH_THEME = True
    TEST_WITH_PLUGINS = True
    PLUGINS = ['front']
    THEME = 'gouvfr'


@pytest.mark.skip(reason='Territories logic changed because of gouvfr')
class TerritoriesTest(GouvfrFrontTestCase):
    modules = ['admin']
    settings = GouvFrTerritoriesSettings

    def setUp(self):
        self.paca, self.bdr, self.arles = create_geozones_fixtures()

    def test_towns_with_default_base_datasets(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.arles))
        self.assert200(response)
        data = response.data.decode('utf-8')
        self.assertIn(self.arles.name, data)
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
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
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)

    def test_towns_with_other_datasets(self):
        organization = OrganizationFactory()
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
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
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)

    def test_counties_with_other_datasets(self):
        organization = OrganizationFactory()
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
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
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)

    def test_regions_with_other_datasets(self):
        organization = OrganizationFactory()
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
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
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('You want to add your own datasets to that list?', data)

    def test_towns_with_other_datasets_logged_in(self):
        self.login()
        organization = OrganizationFactory()
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
            spatial=SpatialCoverageFactory(zones=[self.arles.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.arles))
        self.assert200(response)
        data = response.data.decode('utf-8')
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('If you want your datasets to appear in that list', data)

    def test_counties_with_other_datasets_logged_in(self):
        self.login()
        organization = OrganizationFactory()
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
            spatial=SpatialCoverageFactory(zones=[self.bdr.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.bdr))
        self.assert200(response)
        data = response.data.decode('utf-8')
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('If you want your datasets to appear in that list', data)

    def test_regions_with_other_datasets_logged_in(self):
        self.login()
        organization = OrganizationFactory()
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
            spatial=SpatialCoverageFactory(zones=[self.paca.id]))
        response = self.client.get(
            url_for('territories.territory', territory=self.paca))
        self.assert200(response)
        data = response.data.decode('utf-8')
        base_datasets = self.get_context_variable('base_datasets')
        self.assertEqual(len(base_datasets), 0)
        other_datasets = self.get_context_variable('other_datasets')
        self.assertEqual(len(other_datasets), 3)
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('If you want your datasets to appear in that list', data)

    def test_towns_with_other_datasets_and_pertinent_ones(self):
        user = self.login()
        member = Member(user=user, role='admin')
        organization = OrganizationFactory(members=[member])
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
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
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('If you want your datasets to appear in that list', data)

    def test_counties_with_other_datasets_and_pertinent_ones(self):
        user = self.login()
        member = Member(user=user, role='admin')
        organization = OrganizationFactory(members=[member])
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
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
        self.assertEqual(self.get_context_variable('territory_datasets'), [])
        self.assertIn('If you want your datasets to appear in that list', data)

    def test_regions_with_other_datasets_and_pertinent_ones(self):
        user = self.login()
        member = Member(user=user, role='admin')
        organization = OrganizationFactory(members=[member])
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
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
        self.assertEqual(self.get_context_variable('territory_datasets'), [])

    def test_with_town_datasets(self):
        organization = OrganizationFactory(zone=self.arles.id)
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
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
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertNotIn('dataset-item--cta', data)

    def test_with_county_datasets(self):
        organization = OrganizationFactory(zone=self.bdr.id)
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
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
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertNotIn('dataset-item--cta', data)

    def test_with_region_datasets(self):
        organization = OrganizationFactory(zone=self.paca.id)
        VisibleDatasetFactory.create_batch(
            3, organization=organization,
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
        self.assertEqual(self.get_context_variable('other_datasets'), [])
        self.assertNotIn('dataset-item--cta', data)

    def test_with_old_region_datasets(self):
        lr, occitanie = create_old_new_regions_fixtures()
        for region in [lr, occitanie]:
            organization = OrganizationFactory(zone=region.id)
            VisibleDatasetFactory.create_batch(
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

    def test_town_legacy_redirect(self):
        response = self.client.get(
            url_for('territories.redirect_town', code=self.arles.code))
        self.assertStatus(response, 302)
        self.assertTrue(
            '/territories/commune/13004%40latest/' in response.location)

    def test_town2_legacy_redirect(self):
        response = self.client.get(
            url_for('territories.redirect_town2', code=self.arles.code))
        self.assertStatus(response, 302)
        self.assertTrue(
            '/territories/commune/13004%40latest/' in response.location)

    def test_county_legacy_redirect(self):
        response = self.client.get(
            url_for('territories.redirect_county', code=self.bdr.code))
        self.assertStatus(response, 302)
        self.assertTrue(
            '/territories/departement/13%40latest/' in response.location)

    def test_region_legacy_redirect(self):
        response = self.client.get(
            url_for('territories.redirect_region', code=self.paca.code))
        self.assertStatus(response, 302)
        self.assertTrue(
            '/territories/region/93%40latest/' in response.location)

    def test_territory_town_latest_redirect(self):
        response = self.client.get(
            url_for('territories.redirect_territory',
                    level='commune', code=self.arles.code))
        self.assertStatus(response, 302)
        self.assertTrue(
            '/territories/commune/13004@1942-01-01/' in response.location)

    def test_territory_county_latest_redirect(self):
        response = self.client.get(
            url_for('territories.redirect_territory',
                    level='departement', code=self.bdr.code))
        self.assertStatus(response, 302)
        self.assertTrue(
            '/territories/departement/13@1860-07-01/' in response.location)

    def test_territory_region_latest_redirect(self):
        response = self.client.get(
            url_for('territories.redirect_territory',
                    level='region', code=self.paca.code))
        self.assertStatus(response, 302)
        self.assertTrue(
            '/territories/region/93@1970-01-09/' in response.location)


@pytest.mark.skip(reason='Territories logic changed because of gouvfr')
class TerritoriesGenTest(GouvfrFrontTestCase):
    modules = ['admin']
    settings = GouvFrTerritoriesSettings

    def setUp(self):
        self.paca, self.bdr, self.arles = create_geozones_fixtures()

    def test_towns(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.arles))
        self.assert404(response)  # By default towns are deactivated.

    def test_counties(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.bdr))
        self.assert404(response)  # By default counties are deactivated.

    def test_regions(self):
        response = self.client.get(
            url_for('territories.territory', territory=self.paca))
        self.assert404(response)  # By default regions are deactivated.
