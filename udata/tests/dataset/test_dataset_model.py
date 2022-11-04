from datetime import datetime, timedelta

import pytest
import requests
from flask import current_app
from mongoengine import post_save

from udata.app import cache
from udata.models import (
    db, Dataset, License, LEGACY_FREQUENCIES, ResourceSchema
)
from udata.core.dataset.models import HarvestDatasetMetadata, HarvestResourceMetadata
from udata.core.dataset.factories import (
    ResourceFactory, DatasetFactory, CommunityResourceFactory, LicenseFactory
)
from udata.core.dataset.exceptions import (
    SchemasCatalogNotFoundException, SchemasCacheUnavailableException
)
from udata.core.user.factories import UserFactory
from udata.utils import faker
from udata.tests.helpers import (
    assert_emit, assert_not_emit, assert_equal_dates
)

pytestmark = pytest.mark.usefixtures('clean_db')


class DatasetModelTest:
    def test_add_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory()
        expected_signals = (Dataset.on_resource_added,)

        with assert_emit(*expected_signals):
            dataset.add_resource(ResourceFactory())
        assert len(dataset.resources) == 1

        with assert_emit(*expected_signals):
            dataset.add_resource(resource)
        assert len(dataset.resources) == 2
        assert dataset.resources[0].id == resource.id
        assert dataset.resources[0].dataset == dataset

    def test_add_resource_without_checksum(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory(checksum=None)
        expected_signals = (Dataset.on_resource_added,)

        with assert_emit(*expected_signals):
            dataset.add_resource(ResourceFactory(checksum=None))
        assert len(dataset.resources) == 1

        with assert_emit(*expected_signals):
            dataset.add_resource(resource)
        assert len(dataset.resources) == 2
        assert dataset.resources[0].id == resource.id

    def test_add_resource_missing_checksum_type(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory()
        resource.checksum.type = None

        with pytest.raises(db.ValidationError):
            dataset.add_resource(resource)

    def test_update_resource(self):
        user = UserFactory()
        resource = ResourceFactory()
        dataset = DatasetFactory(owner=user, resources=[resource])
        expected_signals = (Dataset.on_resource_updated,)

        resource.description = 'New description'

        with assert_emit(*expected_signals):
            dataset.update_resource(resource)
        assert len(dataset.resources) == 1
        assert dataset.resources[0].id == resource.id
        assert dataset.resources[0].description == 'New description'

    def test_update_resource_missing_checksum_type(self):
        user = UserFactory()
        resource = ResourceFactory()
        dataset = DatasetFactory(owner=user, resources=[resource])
        resource.checksum.type = None

        with pytest.raises(db.ValidationError):
            dataset.update_resource(resource)

    def test_last_update_with_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        resource = ResourceFactory()
        dataset.add_resource(resource)
        assert_equal_dates(dataset.last_update, resource.published)

    def test_last_update_without_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        assert_equal_dates(dataset.last_update, dataset.last_modified)

    def test_community_resource(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user)
        community_resource1 = CommunityResourceFactory()
        community_resource1.dataset = dataset
        community_resource1.save()
        assert len(dataset.community_resources) == 1

        community_resource2 = CommunityResourceFactory()
        community_resource2.dataset = dataset
        community_resource2.save()
        assert len(dataset.community_resources) == 2
        assert dataset.community_resources[1].id == community_resource1.id
        assert dataset.community_resources[0].id == community_resource2.id

    def test_community_resource_deleted_dataset(self):
        dataset = DatasetFactory()
        community_resource = CommunityResourceFactory(dataset=dataset)
        community_resource.dataset.delete()
        community_resource.reload()
        assert community_resource.dataset is None

    def test_next_update_empty(self):
        dataset = DatasetFactory()
        assert dataset.next_update is None

    def test_next_update_weekly(self):
        dataset = DatasetFactory(frequency='weekly')
        assert_equal_dates(dataset.next_update,
                           datetime.now() + timedelta(days=7))

    def test_quality_default(self):
        dataset = DatasetFactory(description='')
        assert dataset.quality == {
            'license': False,
            'temporal_coverage': False,
            'spatial': False,
            'update_frequency': False,
            'dataset_description_quality': False,
            'score': 0
        }

    def test_quality_next_update(self):
        dataset = DatasetFactory(description='', frequency='weekly')
        assert dataset.quality['update_fulfilled_in_time'] is True
        assert dataset.quality['update_frequency'] is True
        assert dataset.quality['score'] == Dataset.normalize_score(2)

    def test_quality_description_length(self):
        dataset = DatasetFactory(description='a' * (current_app.config.get('QUALITY_DESCRIPTION_LENGTH') - 1))
        assert dataset.quality['dataset_description_quality'] is False
        assert dataset.quality['score'] == 0
        dataset = DatasetFactory(description='a' * (current_app.config.get('QUALITY_DESCRIPTION_LENGTH') + 1))
        assert dataset.quality['dataset_description_quality'] is True
        assert dataset.quality['score'] == Dataset.normalize_score(1)

    def test_quality_has_open_formats(self):
        dataset = DatasetFactory(description='', )
        dataset.add_resource(ResourceFactory(format='pdf'))
        assert not dataset.quality['has_open_format']
        assert dataset.quality['score'] == Dataset.normalize_score(2)

    def test_quality_has_opened_formats(self):
        dataset = DatasetFactory(description='', )
        dataset.add_resource(ResourceFactory(format='pdf'))
        dataset.add_resource(ResourceFactory(format='csv'))
        assert dataset.quality['has_open_format']
        assert dataset.quality['score'] == Dataset.normalize_score(3)

    def test_quality_has_undefined_and_closed_format(self):
        dataset = DatasetFactory(description='', )
        dataset.add_resource(ResourceFactory(format=None))
        dataset.add_resource(ResourceFactory(format='xls'))
        assert not dataset.quality['has_open_format']
        assert dataset.quality['score'] == Dataset.normalize_score(2)

    def test_quality_all(self):
        user = UserFactory()
        dataset = DatasetFactory(owner=user, frequency='weekly',
                                 tags=['foo', 'bar'], description='a' * 42)
        dataset.add_resource(ResourceFactory(format='pdf'))
        assert dataset.quality['score'] == Dataset.normalize_score(4)
        assert sorted(dataset.quality.keys()) == [
            'all_resources_available',
            'dataset_description_quality',
            'has_open_format',
            'has_resources',
            'license',
            'resources_documentation',
            'score',
            'spatial',
            'temporal_coverage',
            'update_frequency',
            'update_fulfilled_in_time'
        ]

    def test_tags_normalized(self):
        tags = [' one another!', ' one another!', 'This IS a "tag"…']
        dataset = DatasetFactory(tags=tags)
        assert len(dataset.tags) == 2
        assert dataset.tags[1] == 'this-is-a-tag'

    def test_legacy_frequencies(self):
        for oldFreq, newFreq in LEGACY_FREQUENCIES.items():
            dataset = DatasetFactory(frequency=oldFreq)
            assert dataset.frequency == newFreq

    def test_send_on_delete(self):
        dataset = DatasetFactory()
        with assert_emit(Dataset.on_delete):
            dataset.deleted = datetime.now()
            dataset.save()

    def test_ignore_post_save_signal(self):
        dataset = DatasetFactory()
        unexpected_signals = Dataset.after_save, Dataset.on_update

        with assert_not_emit(*unexpected_signals), assert_emit(post_save):
            dataset.title = 'New title'
            dataset.save(signal_kwargs={'ignores': ['post_save']})


class ResourceModelTest:
    def test_url_is_required(self):
        with pytest.raises(db.ValidationError):
            DatasetFactory(resources=[ResourceFactory(url=None)])

    def test_bad_url(self):
        with pytest.raises(db.ValidationError):
            DatasetFactory(resources=[ResourceFactory(url='not-an-url')])

    def test_url_is_stripped(self):
        url = 'http://www.somewhere.com/with/spaces/   '
        dataset = DatasetFactory(resources=[ResourceFactory(url=url)])
        assert dataset.resources[0].url == url.strip()

    def test_ignore_post_save_signal(self):
        resource = ResourceFactory()
        # assigning to a variable to avoid garbage collection issue
        _ = DatasetFactory(resources=[resource])
        unexpected_signals = Dataset.after_save, Dataset.on_update

        with assert_not_emit(*unexpected_signals), assert_emit(post_save):
            resource.title = 'New title'
            resource.save(signal_kwargs={'ignores': ['post_save']})


class LicenseModelTest:
    @pytest.fixture(autouse=True)
    def setUp(self):
        # Feed the DB with random data to ensure true matching
        LicenseFactory.create_batch(3)

    def test_not_found(self):
        found = License.guess('should not be found')
        assert found is None

    def test_not_found_with_default(self):
        license = LicenseFactory()
        found = License.guess('should not be found', default=license)
        assert found.id == license.id

    def test_none(self):
        found = License.guess(None)
        assert found is None

    def test_empty_string(self):
        found = License.guess('')
        assert found is None

    def test_exact_match_by_id(self):
        license = LicenseFactory()
        found = License.guess(license.id)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_imatch_by_id(self):
        license = LicenseFactory(id='CAPS-ID')
        found = License.guess(license.id)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_id_with_spaces(self):
        license = LicenseFactory()
        found = License.guess(' {0} '.format(license.id))
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_url(self):
        license = LicenseFactory()
        found = License.guess(license.url)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_url_with_final_slash(self):
        license = LicenseFactory(url='https://example.com/license')
        found = License.guess('https://example.com/license/')
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_url_without_final_slash(self):
        license = LicenseFactory(url='https://example.com/license/')
        found = License.guess('https://example.com/license')
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_url_not_too_fuzzy(self):
        LicenseFactory(url='https://example.com/licensea')
        found = License.guess('https://example.com/licenseb')
        assert found is None

    def test_match_by_url_scheme_mismatch(self):
        license = LicenseFactory(url='https://example.com/license')
        found = License.guess('http://example.com/license')
        assert isinstance(found, License)
        assert license.id == found.id

    def test_imatch_by_url(self):
        url = '%s/CAPS.php' % faker.uri()
        license = LicenseFactory(url=url)
        found = License.guess(license.url)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_alternate_url(self):
        alternate_url = faker.uri()
        license = LicenseFactory(alternate_urls=[alternate_url])
        found = License.guess(alternate_url)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_imatch_by_alternate_url(self):
        alternate_url = '%s/CAPS.php' % faker.uri()
        license = LicenseFactory(alternate_urls=[alternate_url])
        found = License.guess(alternate_url)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_alternate_url_scheme_slash_mismatch(self):
        alternate_url = 'https://example.com/license'
        license = LicenseFactory(alternate_urls=[alternate_url])
        found = License.guess('http://example.com/license/')
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_title(self):
        license = LicenseFactory()
        found = License.guess(license.title)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_title_with_mismatch_slug(self):
        license = LicenseFactory(title="Licence Ouverte v2", slug="licence-2")
        found = License.guess(license.title)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_title_with_spaces(self):
        license = LicenseFactory()
        found = License.guess(' {0} '.format(license.title))
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_title_with_low_edit_distance(self):
        license = LicenseFactory(title='License')
        found = License.guess('Licence')
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_title_with_extra_inner_space(self):
        license = LicenseFactory(title='License ODBl')
        found = License.guess('License  ODBl')  # 2 spaces instead of 1
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_title_with_mismatching_case(self):
        license = LicenseFactory(title='License ODBl')
        found = License.guess('License ODBL')
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_alternate_title(self):
        alternate_title = faker.sentence()
        license = LicenseFactory(alternate_titles=[alternate_title])
        found = License.guess(alternate_title)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_alternate_title_with_spaces(self):
        alternate_title = faker.sentence()
        license = LicenseFactory(alternate_titles=[alternate_title])
        found = License.guess(' {0} '.format(alternate_title))
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_alternate_title_with_low_edit_distance(self):
        license = LicenseFactory(alternate_titles=['License'])
        found = License.guess('Licence')
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_alternate_title_with_extra_inner_space(self):
        license = LicenseFactory(alternate_titles=['License ODBl'])
        found = License.guess('License  ODBl')  # 2 spaces instead of 1
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_alternate_title_with_mismatching_case(self):
        license = LicenseFactory(alternate_titles=['License ODBl'])
        found = License.guess('License ODBL')
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_alternate_title_with_multiple_candidates_from_one_licence(self):
        license = LicenseFactory(alternate_titles=['Licence Ouverte v2', 'Licence Ouverte v2.0'])
        found = License.guess('Licence Ouverte v2.0')
        assert isinstance(found, License)
        assert license.id == found.id

    def test_no_with_multiple_alternate_titles_from_different_licences(self):
        LicenseFactory(alternate_titles=['Licence Ouverte v2'])
        LicenseFactory(alternate_titles=['Licence Ouverte v2.0'])
        found = License.guess('Licence Ouverte v2.0')
        assert found is None

    def test_prioritize_title_over_alternate_title(self):
        title = faker.sentence()
        license = LicenseFactory(title=title)
        LicenseFactory(alternate_titles=[title])
        found = License.guess(title)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_multiple_strings(self):
        license = LicenseFactory()
        found = License.guess('should not match', license.id)
        assert isinstance(found, License)
        assert license.id == found.id


class ResourceSchemaTest:
    @pytest.mark.options(SCHEMA_CATALOG_URL='https://example.com/notfound')
    def test_resource_schema_objects_404_endpoint(self):
        with pytest.raises(SchemasCatalogNotFoundException):
            ResourceSchema.objects()

    @pytest.mark.options(SCHEMA_CATALOG_URL='https://example.com/schemas')
    def test_resource_schema_objects_timeout_no_cache(self, client, rmock):
        rmock.get('https://example.com/schemas', exc=requests.exceptions.ConnectTimeout)
        with pytest.raises(SchemasCacheUnavailableException):
            ResourceSchema.objects()

    @pytest.mark.options(SCHEMA_CATALOG_URL='https://example.com/schemas')
    def test_resource_schema_objects(self, app, rmock):
        rmock.get('https://example.com/schemas', json={
            "schemas": [
                {
                    "name": "etalab/schema-irve",
                    "title": "Schéma IRVE",
                    "versions": [
                        {
                            "version_name": "1.0.0"
                        },
                        {
                            "version_name": "1.0.1"
                        },
                        {
                            "version_name": "1.0.2"
                        }
                    ]
                }
            ]
        })

        assert ResourceSchema.objects() == [
            {
                "id": "etalab/schema-irve",
                "label": "Schéma IRVE",
                "versions": [
                    "1.0.0",
                    "1.0.1",
                    "1.0.2"
                ]
            }
        ]

    @pytest.mark.options(SCHEMA_CATALOG_URL=None)
    def test_resource_schema_objects_no_catalog_url(self):
        assert ResourceSchema.objects() == []

    @pytest.mark.options(SCHEMA_CATALOG_URL='https://example.com/schemas')
    def test_resource_schema_objects_w_cache(self, rmock, mocker):
        cache_mock_set = mocker.patch.object(cache, 'set')
        mocker.patch.object(cache, 'get', return_value='dummy_from_cache')

        # fill cache
        rmock.get('https://example.com/schemas', json={
            "schemas": [
                {
                    "name": "etalab/schema-irve",
                    "title": "Schéma IRVE",
                    "versions": [
                        {
                            "version_name": "1.0.0"
                        },
                        {
                            "version_name": "1.0.1"
                        },
                        {
                            "version_name": "1.0.2"
                        }
                    ]
                }
            ]
        })
        ResourceSchema.objects()
        assert cache_mock_set.called

        rmock.get('https://example.com/schemas', status_code=500)
        assert 'dummy_from_cache' == ResourceSchema.objects()
        assert rmock.call_count == 2


class HarvestMetadataTest:
    def test_harvest_dataset_metadata_validate_success(self):
        dataset = DatasetFactory()

        harvest_metadata = HarvestDatasetMetadata(
            backend='DCAT',
            created_at=datetime.now(),
            modified_at=datetime.now(),
            source_id='source_id',
            remote_id='remote_id',
            domain='domain.gouv.fr',
            last_update=datetime.now(),
            remote_url='http://domain.gouv.fr/dataset/remote_url',
            uri='http://domain.gouv.fr/dataset/uri',
            dct_identifier='http://domain.gouv.fr/dataset/identifier',
            archived_at=datetime.now(),
            archived='not-on-remote'
        )
        dataset.harvest = harvest_metadata
        dataset.save()

    def test_harvest_dataset_metadata_validation_error(self):
        harvest_metadata = HarvestDatasetMetadata(created_at='maintenant')
        dataset = DatasetFactory()
        dataset.harvest = harvest_metadata
        with pytest.raises(db.ValidationError):
            dataset.save()

    def test_harvest_dataset_metadata_no_validation_dynamic(self):
        # Adding a dynamic field (not defined in HarvestDatasetMetadata) does not raise error
        # at validation time
        harvest_metadata = HarvestDatasetMetadata(dynamic_created_at='maintenant')
        dataset = DatasetFactory()
        dataset.harvest = harvest_metadata
        dataset.save()

    def test_harvest_resource_metadata_validate_success(self):
        resource = ResourceFactory()

        harvest_metadata = HarvestResourceMetadata(
            created_at=datetime.now(),
            modified_at=datetime.now(),
            uri='http://domain.gouv.fr/dataset/uri'
        )
        resource.harvest = harvest_metadata
        resource.validate()

    def test_harvest_resource_metadata_validation_error(self):
        harvest_metadata = HarvestResourceMetadata(created_at='maintenant')
        resource = ResourceFactory()
        resource.harvest = harvest_metadata
        with pytest.raises(db.ValidationError):
            resource.validate()

    def test_harvest_resource_metadata_no_validation_dynamic(self):
        # Adding a dynamic field (not defined in HarvestResourceMetadata) does not raise error
        # at validation time
        harvest_metadata = HarvestResourceMetadata(dynamic_created_at='maintenant')
        resource = ResourceFactory()
        resource.harvest = harvest_metadata
        resource.validate()
