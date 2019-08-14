import copy
import pytest

from flask import url_for

from udata import theme
from udata.core.dataset.factories import DatasetFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.spatial.factories import GeoZoneFactory
from udata.core.user.factories import UserFactory
from udata.core.organization.factories import OrganizationFactory
from udata.features.territories.models import (
    TerritoryDataset, TERRITORY_DATASETS
)
from udata.frontend.markdown import mdstrip
from udata.settings import Testing
from udata.utils import faker
from udata.tests.helpers import assert200, assert400, assert404, assert_status, assert_cors


class OEmbedAPITest:
    modules = ['core.dataset', 'core.organization', 'core.reuse']

    def test_oembed_for_dataset(self, api):
        '''It should fetch a dataset in the oembed format.'''
        dataset = DatasetFactory()

        url = url_for('api.oembed', url=dataset.external_url)
        response = api.get(url)
        assert200(response)
        assert_cors(response)
        assert 'html' in response.json
        assert 'width' in response.json
        assert 'maxwidth' in response.json
        assert 'height' in response.json
        assert 'maxheight' in response.json
        assert response.json['type'] == 'rich'
        assert response.json['version'] == '1.0'
        card = theme.render('dataset/card.html', dataset=dataset)
        assert card in response.json['html']

    def test_oembed_for_dataset_with_organization(self, api):
        '''It should fetch a dataset in the oembed format with org.'''
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)

        url = url_for('api.oembed', url=dataset.external_url)
        response = api.get(url)
        assert200(response)
        assert_cors(response)

        card = theme.render('dataset/card.html', dataset=dataset)
        assert card in response.json['html']

    def test_oembed_for_dataset_redirect_link(self, api):
        '''It should fetch an oembed dataset using the redirect link.'''
        dataset = DatasetFactory()
        redirect_url = url_for('datasets.show_redirect',
                               dataset=dataset, _external=True)

        url = url_for('api.oembed', url=redirect_url)
        response = api.get(url)
        assert200(response)
        assert_cors(response)
        assert 'html' in response.json
        assert 'width' in response.json
        assert 'maxwidth' in response.json
        assert 'height' in response.json
        assert 'maxheight' in response.json
        assert response.json['type'] == 'rich'
        assert response.json['version'] == '1.0'
        card = theme.render('dataset/card.html', dataset=dataset)
        assert card in response.json['html']

    def test_oembed_for_unknown_dataset(self, api):
        '''It should raise a 404 on missing dataset.'''
        dataset_url = url_for('datasets.show', dataset='unknown',
                              _external=True)
        url = url_for('api.oembed', url=dataset_url)
        response = api.get(url)
        assert404(response)
        assert_cors(response)

    def test_oembed_for_reuse(self, api):
        '''It should fetch a reuse in the oembed format.'''
        reuse = ReuseFactory()

        url = url_for('api.oembed', url=reuse.external_url)
        response = api.get(url)
        assert200(response)
        assert_cors(response)
        assert 'html' in response.json
        assert 'width' in response.json
        assert 'maxwidth' in response.json
        assert 'height' in response.json
        assert 'maxheight' in response.json
        assert response.json['type'] == 'rich'
        assert response.json['version'] == '1.0'
        card = theme.render('reuse/card.html', reuse=reuse)
        assert card in response.json['html']

    def test_oembed_for_org(self, api):
        '''It should fetch an organization in the oembed format.'''
        org = OrganizationFactory()

        url = url_for('api.oembed', url=org.external_url)
        response = api.get(url)
        assert200(response)
        assert_cors(response)
        assert 'html' in response.json
        assert 'width' in response.json
        assert 'maxwidth' in response.json
        assert 'height' in response.json
        assert 'maxheight' in response.json
        assert response.json['type'] == 'rich'
        assert response.json['version'] == '1.0'
        card = theme.render('organization/card.html', organization=org)
        assert card in response.json['html']

    def test_oembed_without_url(self, api):
        '''It should fail at fetching an oembed without a dataset.'''
        response = api.get(url_for('api.oembed'))
        assert400(response)
        assert 'url' in response.json['errors']

    def test_oembed_with_an_invalid_url(self, api):
        '''It should fail at fetching an oembed with an invalid URL.'''
        response = api.get(url_for('api.oembed', url='123456789'))
        assert400(response)
        assert 'url' in response.json['errors']

    def test_oembed_with_an_unknown_url(self, api):
        '''It should fail at fetching an oembed with an invalid URL.'''
        url = url_for('api.oembed', url='http://local.test/somewhere')
        response = api.get(url)
        assert404(response)
        assert_cors(response)

    def test_oembed_with_port_in_https_url(self, api):
        '''It should works on HTTPS URLs with explicit port.'''
        dataset = DatasetFactory()
        url = dataset.external_url.replace('http://local.test/',
                                           'https://local.test:443/')
        api_url = url_for('api.oembed', url=url)

        assert200(api.get(api_url, base_url='https://local.test:443/'))

    def test_oembed_does_not_support_xml(self, api):
        '''It does not support xml format.'''
        dataset = DatasetFactory()
        url = url_for('api.oembed', url=dataset.external_url, format='xml')
        response = api.get(url)
        assert_status(response, 501)
        assert_cors(response)
        assert response.json['message'] == 'Only JSON format is supported'


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


class OEmbedsDatasetAPITest:
    modules = ['core.organization', 'features.territories', 'core.dataset']
    settings = OEmbedSettings

    @pytest.fixture(autouse=True)
    def copy_territoy_datasets(self):
        self.territory_datasets_backup = {
            k: copy.deepcopy(v) for k, v in TERRITORY_DATASETS.items()
        }
        yield
        TERRITORY_DATASETS.update(self.territory_datasets_backup)

    def test_oembeds_dataset_api_get(self, api):
        '''It should fetch a dataset in the oembed format.'''
        dataset = DatasetFactory()

        url = url_for('api.oembeds',
                      references='dataset-{id}'.format(id=dataset.id))
        response = api.get(url)
        assert200(response)
        data = response.json[0]
        assert 'html' in data
        assert 'width' in data
        assert 'maxwidth' in data
        assert 'height' in data
        assert 'maxheight' in data
        assert data['type'] == 'rich'
        assert data['version'] == '1.0'
        assert dataset.title in data['html']
        assert dataset.external_url in data['html']
        assert 'placeholders/default.png' in data['html']
        assert mdstrip(dataset.description, 110) in data['html']

    def test_oembeds_dataset_api_get_with_organization(self, api):
        '''It should fetch a dataset in the oembed format with org.'''
        organization = OrganizationFactory()
        dataset = DatasetFactory(organization=organization)

        url = url_for('api.oembeds',
                      references='dataset-{id}'.format(id=dataset.id))
        response = api.get(url)
        assert200(response)
        data = response.json[0]
        assert organization.name in data['html']
        assert organization.external_url in data['html']

    def test_oembeds_dataset_api_get_without_references(self, api):
        '''It should fail at fetching an oembed without a dataset.'''
        response = api.get(url_for('api.oembeds'))
        assert400(response)
        assert 'references' in response.json['errors']

    def test_oembeds_dataset_api_get_without_good_id(self, api):
        '''It should fail at fetching an oembed without a good id.'''
        response = api.get(url_for('api.oembeds', references='123456789'))
        assert400(response)
        assert response.json['message'] == 'Invalid ID.'

    def test_oembeds_dataset_api_get_without_good_item(self, api):
        '''It should fail at fetching an oembed with a wrong item.'''
        user = UserFactory()

        url = url_for('api.oembeds', references='user-{id}'.format(id=user.id))
        response = api.get(url)
        assert400(response)
        assert response.json['message'] == 'Invalid object type.'

    def test_oembeds_dataset_api_get_without_valid_id(self, api):
        '''It should fail at fetching an oembed without a valid id.'''
        url = url_for('api.oembeds', references='dataset-123456789')
        response = api.get(url)
        assert400(response)
        assert response.json['message'] == 'Unknown dataset ID.'

    def test_oembeds_api_for_territory(self, api):
        '''It should fetch a territory in the oembed format.'''
        country = faker.country_code().lower()
        level = 'commune'
        zone = GeoZoneFactory(level='{0}:{1}'.format(country, level))
        TestDataset = territory_dataset_factory()
        TERRITORY_DATASETS[level][TestDataset.id] = TestDataset
        reference = 'territory-{0}:{1}'.format(zone.id, TestDataset.id)
        url = url_for('api.oembeds', references=reference)
        response = api.get(url)
        assert200(response)
        data = response.json[0]
        assert 'html' in data
        assert 'width' in data
        assert 'maxwidth' in data
        assert 'height' in data
        assert 'maxheight' in data
        assert data['type'] == 'rich'
        assert data['version'] == '1.0'
        assert zone.name in data['html']
        assert 'placeholders/default.png' in data['html']

    def test_oembeds_api_for_territory_resolve_geoid(self, api):
        '''It should fetch a territory from a geoid in the oembed format.'''
        country = faker.country_code().lower()
        level = 'commune'
        zone = GeoZoneFactory(level='{0}:{1}'.format(country, level))
        TestDataset = territory_dataset_factory()
        TERRITORY_DATASETS[level][TestDataset.id] = TestDataset
        geoid = '{0.level}:{0.code}@latest'.format(zone)
        reference = 'territory-{0}:{1}'.format(geoid, TestDataset.id)

        url = url_for('api.oembeds', references=reference)
        response = api.get(url)
        assert200(response)
        data = response.json[0]
        assert 'html' in data
        assert 'width' in data
        assert 'maxwidth' in data
        assert 'height' in data
        assert 'maxheight' in data
        assert data['type'] == 'rich'
        assert data['version'] == '1.0'
        assert zone.name in data['html']
        assert 'placeholders/default.png' in data['html']

    def test_oembeds_api_for_territory_bad_id(self, api):
        '''Should raise 400 on bad territory ID'''
        url = url_for('api.oembeds', references='territory-xyz')
        response = api.get(url)
        assert400(response)
        assert response.json['message'] == 'Invalid territory ID.'

    def test_oembeds_api_for_territory_zone_not_found(self, api):
        '''Should raise 400 on unknown zone ID'''
        url = url_for('api.oembeds',
                      references='territory-fr:commune:13004@1970-01-01:xyz')
        response = api.get(url)
        assert400(response)
        assert response.json['message'] == 'Unknown territory identifier.'

    def test_oembeds_api_for_territory_level_not_registered(self, api):
        '''Should raise 400 on unregistered territory level'''
        country = faker.country_code().lower()
        level = 'commune'
        zone = GeoZoneFactory(level='{0}:{1}'.format(country, level))
        TestDataset = territory_dataset_factory()
        del TERRITORY_DATASETS[level]
        reference = 'territory-{0}:{1}'.format(zone.id, TestDataset.id)
        url = url_for('api.oembeds', references=reference)
        response = api.get(url)
        assert400(response)
        assert response.json['message'] == 'Unknown kind of territory.'

    def test_oembeds_api_for_territory_dataset_not_registered(self, api):
        '''Should raise 400 on unregistered territory dataset'''
        country = faker.country_code().lower()
        level = 'commune'
        zone = GeoZoneFactory(level='{0}:{1}'.format(country, level))
        TestDataset = territory_dataset_factory()
        TERRITORY_DATASETS[level] = {}
        reference = 'territory-{0}:{1}'.format(zone.id, TestDataset.id)
        url = url_for('api.oembeds', references=reference)
        response = api.get(url)
        assert400(response)
        assert response.json['message'] == 'Unknown territory dataset id.'
