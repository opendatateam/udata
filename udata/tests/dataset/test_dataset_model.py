from datetime import datetime, timedelta

import pytest
import requests
from flask import current_app
from mongoengine import post_save

from udata.app import cache
from udata.core.dataset.constants import LEGACY_FREQUENCIES, UPDATE_FREQUENCIES
from udata.core.dataset.exceptions import (
    SchemasCacheUnavailableException,
    SchemasCatalogNotFoundException,
)
from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    LicenseFactory,
    ResourceFactory,
    ResourceSchemaMockData,
)
from udata.core.dataset.models import HarvestDatasetMetadata, HarvestResourceMetadata
from udata.core.user.factories import UserFactory
from udata.models import Dataset, License, ResourceSchema, Schema, db
from udata.tests.helpers import assert_emit, assert_equal_dates, assert_not_emit
from udata.utils import faker

pytestmark = pytest.mark.usefixtures("clean_db")


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

        resource.description = "New description"

        with assert_emit(*expected_signals):
            dataset.update_resource(resource)
        assert len(dataset.resources) == 1
        assert dataset.resources[0].id == resource.id
        assert dataset.resources[0].description == "New description"

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
        assert_equal_dates(dataset.last_update, resource.created_at)

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

    def test_next_update_hourly(self):
        dataset = DatasetFactory(frequency="hourly")
        assert_equal_dates(dataset.next_update, datetime.utcnow() + timedelta(hours=1))

    @pytest.mark.parametrize("freq", ["fourTimesADay", "threeTimesADay", "semidaily", "daily"])
    def test_next_update_daily(self, freq):
        dataset = DatasetFactory(frequency=freq)
        assert_equal_dates(dataset.next_update, datetime.utcnow() + timedelta(days=1))

    @pytest.mark.parametrize("freq", ["fourTimesAWeek", "threeTimesAWeek", "semiweekly", "weekly"])
    def test_next_update_weekly(self, freq):
        dataset = DatasetFactory(frequency=freq)
        assert_equal_dates(dataset.next_update, datetime.utcnow() + timedelta(days=7))

    def test_next_update_biweekly(self):
        dataset = DatasetFactory(frequency="biweekly")
        assert_equal_dates(dataset.next_update, datetime.utcnow() + timedelta(weeks=2))

    def test_next_update_quarterly(self):
        dataset = DatasetFactory(frequency="quarterly")
        assert_equal_dates(dataset.next_update, datetime.utcnow() + timedelta(days=365 / 4))

    @pytest.mark.parametrize("freq", ["threeTimesAYear", "semiannual", "annual"])
    def test_next_update_annual(self, freq):
        dataset = DatasetFactory(frequency=freq)
        assert_equal_dates(dataset.next_update, datetime.utcnow() + timedelta(days=365))

    def test_next_update_biennial(self):
        dataset = DatasetFactory(frequency="biennial")
        assert_equal_dates(dataset.next_update, datetime.utcnow() + timedelta(days=365 * 2))

    def test_next_update_triennial(self):
        dataset = DatasetFactory(frequency="triennial")
        assert_equal_dates(dataset.next_update, datetime.utcnow() + timedelta(days=365 * 3))

    def test_next_update_quinquennial(self):
        dataset = DatasetFactory(frequency="quinquennial")
        assert_equal_dates(dataset.next_update, datetime.utcnow() + timedelta(days=365 * 5))

    @pytest.mark.parametrize("freq", ["continuous", "punctual", "irregular", "unknown"])
    def test_next_update_undefined(self, freq):
        dataset = DatasetFactory(frequency=freq)
        assert dataset.next_update is None

    def test_quality_default(self):
        dataset = DatasetFactory(description="")
        assert dataset.quality == {
            "license": False,
            "temporal_coverage": False,
            "spatial": False,
            "update_frequency": False,
            "dataset_description_quality": False,
            "score": 0,
        }

    @pytest.mark.parametrize("freq", UPDATE_FREQUENCIES)
    def test_quality_frequency_update(self, freq):
        dataset = DatasetFactory(description="", frequency=freq)
        if freq == "unknown":
            assert dataset.quality["update_frequency"] is False
            assert "update_fulfilled_in_time" not in dataset.quality
            return
        assert dataset.quality["update_frequency"] is True
        assert dataset.quality["update_fulfilled_in_time"] is True
        assert dataset.quality["score"] == Dataset.normalize_score(2)

    def test_quality_frequency_update_one_day_late(self):
        dataset = DatasetFactory(
            description="",
            frequency="daily",
            last_modified_internal=datetime.utcnow() - timedelta(days=1, hours=1),
        )
        assert dataset.quality["update_frequency"] is True
        assert dataset.quality["update_fulfilled_in_time"] is True
        assert dataset.quality["score"] == Dataset.normalize_score(2)

    def test_quality_frequency_update_two_days_late(self):
        dataset = DatasetFactory(
            description="",
            frequency="daily",
            last_modified_internal=datetime.utcnow() - timedelta(days=2, hours=1),
        )
        assert dataset.quality["update_frequency"] is True
        assert dataset.quality["update_fulfilled_in_time"] is False
        assert dataset.quality["score"] == Dataset.normalize_score(1)

    def test_quality_description_length(self):
        dataset = DatasetFactory(
            description="a" * (current_app.config.get("QUALITY_DESCRIPTION_LENGTH") - 1)
        )
        assert dataset.quality["dataset_description_quality"] is False
        assert dataset.quality["score"] == 0
        dataset = DatasetFactory(
            description="a" * (current_app.config.get("QUALITY_DESCRIPTION_LENGTH") + 1)
        )
        assert dataset.quality["dataset_description_quality"] is True
        assert dataset.quality["score"] == Dataset.normalize_score(1)

    def test_quality_has_open_formats(self):
        dataset = DatasetFactory(
            description="",
        )
        dataset.add_resource(ResourceFactory(format="pdf"))
        assert not dataset.quality["has_open_format"]
        assert dataset.quality["score"] == Dataset.normalize_score(2)

    def test_quality_has_opened_formats(self):
        dataset = DatasetFactory(
            description="",
        )
        dataset.add_resource(ResourceFactory(format="pdf"))
        dataset.add_resource(ResourceFactory(format="csv"))
        assert dataset.quality["has_open_format"]
        assert dataset.quality["score"] == Dataset.normalize_score(3)

    def test_quality_has_undefined_and_closed_format(self):
        dataset = DatasetFactory(
            description="",
        )
        dataset.add_resource(ResourceFactory(format=None))
        dataset.add_resource(ResourceFactory(format="xls"))
        assert not dataset.quality["has_open_format"]
        assert dataset.quality["score"] == Dataset.normalize_score(2)

    def test_quality_all(self):
        user = UserFactory()
        dataset = DatasetFactory(
            owner=user, frequency="weekly", tags=["foo", "bar"], description="a" * 42
        )
        dataset.add_resource(ResourceFactory(format="pdf"))
        assert dataset.quality["score"] == Dataset.normalize_score(4)
        assert sorted(dataset.quality.keys()) == [
            "all_resources_available",
            "dataset_description_quality",
            "has_open_format",
            "has_resources",
            "license",
            "resources_documentation",
            "score",
            "spatial",
            "temporal_coverage",
            "update_frequency",
            "update_fulfilled_in_time",
        ]

    def test_tags_normalized(self):
        tags = [" one another!", " one another!", 'This IS a "tag"…']
        dataset = DatasetFactory(tags=tags)
        assert len(dataset.tags) == 2
        assert dataset.tags[1] == "this-is-a-tag"

    def test_legacy_frequencies(self):
        for oldFreq, newFreq in LEGACY_FREQUENCIES.items():
            dataset = DatasetFactory(frequency=oldFreq)
            assert dataset.frequency == newFreq

    def test_send_on_delete(self):
        dataset = DatasetFactory()
        with assert_emit(Dataset.on_delete):
            dataset.deleted = datetime.utcnow()
            dataset.save()

    def test_ignore_post_save_signal(self):
        dataset = DatasetFactory()
        unexpected_signals = Dataset.after_save, Dataset.on_update

        with assert_not_emit(*unexpected_signals), assert_emit(post_save):
            dataset.title = "New title"
            dataset.save(signal_kwargs={"ignores": ["post_save"]})

    def test_dataset_without_private(self):
        dataset = DatasetFactory()
        assert dataset.private is False

        dataset.private = None
        dataset.save()
        assert dataset.private is False

        dataset.private = True
        dataset.save()
        assert dataset.private is True


class ResourceModelTest:
    def test_url_is_required(self):
        with pytest.raises(db.ValidationError):
            DatasetFactory(resources=[ResourceFactory(url=None)])

    def test_bad_url(self):
        with pytest.raises(db.ValidationError):
            DatasetFactory(resources=[ResourceFactory(url="not-an-url")])

    def test_url_is_stripped(self):
        url = "http://www.somewhere.com/with/spaces/   "
        dataset = DatasetFactory(resources=[ResourceFactory(url=url)])
        assert dataset.resources[0].url == url.strip()

    def test_ignore_post_save_signal(self):
        resource = ResourceFactory()
        # assigning to a variable to avoid garbage collection issue
        _ = DatasetFactory(resources=[resource])
        unexpected_signals = Dataset.after_save, Dataset.on_update

        with assert_not_emit(*unexpected_signals), assert_emit(post_save):
            resource.title = "New title"
            resource.save(signal_kwargs={"ignores": ["post_save"]})


class LicenseModelTest:
    @pytest.fixture(autouse=True)
    def setUp(self):
        # Feed the DB with random data to ensure true matching
        LicenseFactory.create_batch(3)

    def test_not_found(self):
        found = License.guess("should not be found")
        assert found is None

    def test_not_found_with_default(self):
        license = LicenseFactory()
        found = License.guess("should not be found", default=license)
        assert found.id == license.id

    def test_none(self):
        found = License.guess(None)
        assert found is None

    def test_empty_string(self):
        found = License.guess("")
        assert found is None

    def test_exact_match_by_id(self):
        license = LicenseFactory()
        found = License.guess(license.id)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_imatch_by_id(self):
        license = LicenseFactory(id="CAPS-ID")
        found = License.guess(license.id)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_id_with_spaces(self):
        license = LicenseFactory()
        found = License.guess(" {0} ".format(license.id))
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_url(self):
        license = LicenseFactory()
        found = License.guess(license.url)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_url_in_string(self):
        license = LicenseFactory()
        found = License.guess(f"Here is my license: {license.url}")
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_url_in_string_real_world(self):
        license = LicenseFactory(url="http://www.data.gouv.fr/Licence-Ouverte-Open-Licence")
        found = License.guess(
            "Licence Ouverte 1.0 http://www.data.gouv.fr/Licence-Ouverte-Open-Licence."
        )
        assert isinstance(found, License)
        assert license.id == found.id

    def test_exact_match_by_url_in_string_two_urls(self):
        license = LicenseFactory()
        found = License.guess(
            f"Here is my license: {license.url} and another link: https://example.com/example"
        )
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_url_with_final_slash(self):
        license = LicenseFactory(url="https://example.com/license")
        found = License.guess("https://example.com/license/")
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_url_without_final_slash(self):
        license = LicenseFactory(url="https://example.com/license/")
        found = License.guess("https://example.com/license")
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_url_not_too_fuzzy(self):
        LicenseFactory(url="https://example.com/licensea")
        found = License.guess("https://example.com/licenseb")
        assert found is None

    def test_match_by_url_scheme_mismatch(self):
        license = LicenseFactory(url="https://example.com/license")
        found = License.guess("http://example.com/license")
        assert isinstance(found, License)
        assert license.id == found.id

    def test_imatch_by_url(self):
        url = "%s/CAPS.php" % faker.uri()
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
        alternate_url = "%s/CAPS.php" % faker.uri()
        license = LicenseFactory(alternate_urls=[alternate_url])
        found = License.guess(alternate_url)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_alternate_url_scheme_slash_mismatch(self):
        alternate_url = "https://example.com/license"
        license = LicenseFactory(alternate_urls=[alternate_url])
        found = License.guess("http://example.com/license/")
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
        found = License.guess(" {0} ".format(license.title))
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_title_with_low_edit_distance(self):
        license = LicenseFactory(title="License")
        found = License.guess("Licence")
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_title_with_extra_inner_space(self):
        license = LicenseFactory(title="License ODBl")
        found = License.guess("License  ODBl")  # 2 spaces instead of 1
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_title_with_mismatching_case(self):
        license = LicenseFactory(title="License ODBl")
        found = License.guess("License ODBL")
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
        found = License.guess(" {0} ".format(alternate_title))
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_alternate_title_with_low_edit_distance(self):
        license = LicenseFactory(alternate_titles=["License"])
        found = License.guess("Licence")
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_alternate_title_with_extra_inner_space(self):
        license = LicenseFactory(alternate_titles=["License ODBl"])
        found = License.guess("License  ODBl")  # 2 spaces instead of 1
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_alternate_title_with_mismatching_case(self):
        license = LicenseFactory(alternate_titles=["License ODBl"])
        found = License.guess("License ODBL")
        assert isinstance(found, License)
        assert license.id == found.id

    def test_match_by_alternate_title_with_multiple_candidates_from_one_licence(self):
        license = LicenseFactory(alternate_titles=["Licence Ouverte v2", "Licence Ouverte v2.0"])
        found = License.guess("Licence Ouverte v2.0")
        assert isinstance(found, License)
        assert license.id == found.id

    def test_no_with_multiple_alternate_titles_from_different_licences(self):
        LicenseFactory(alternate_titles=["Licence Ouverte v2"])
        LicenseFactory(alternate_titles=["Licence Ouverte v2.0"])
        found = License.guess("Licence Ouverte v2.0")
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
        found = License.guess("should not match", license.id)
        assert isinstance(found, License)
        assert license.id == found.id

    def test_multiple_strings_reverse(self):
        license = LicenseFactory()
        found = License.guess(license.id, "should not match")
        assert isinstance(found, License)
        assert license.id == found.id


class ResourceSchemaTest:
    @pytest.mark.options(SCHEMA_CATALOG_URL="https://example.com/notfound")
    def test_resource_schema_objects_404_endpoint(self, rmock):
        rmock.get("https://example.com/notfound", status_code=404)
        with pytest.raises(SchemasCatalogNotFoundException):
            ResourceSchema.all()

    @pytest.mark.options(SCHEMA_CATALOG_URL="https://example.com/schemas")
    def test_resource_schema_objects_timeout_no_cache(self, client, rmock):
        rmock.get("https://example.com/schemas", exc=requests.exceptions.ConnectTimeout)
        with pytest.raises(SchemasCacheUnavailableException):
            ResourceSchema.all()

    @pytest.mark.options(SCHEMA_CATALOG_URL="https://example.com/schemas")
    def test_resource_schema_objects(self, app, rmock):
        rmock.get(
            "https://example.com/schemas",
            json={
                "schemas": [
                    {
                        "name": "etalab/schema-irve",
                        "title": "Schéma IRVE",
                        "versions": [
                            {"version_name": "1.0.0"},
                            {"version_name": "1.0.1"},
                            {"version_name": "1.0.2"},
                        ],
                    }
                ]
            },
        )

        assert ResourceSchema.all() == [
            {
                "name": "etalab/schema-irve",
                "title": "Schéma IRVE",
                "versions": [
                    {"version_name": "1.0.0"},
                    {"version_name": "1.0.1"},
                    {"version_name": "1.0.2"},
                ],
            }
        ]

    @pytest.mark.options(SCHEMA_CATALOG_URL=None)
    def test_resource_schema_objects_no_catalog_url(self):
        assert ResourceSchema.all() == []

    @pytest.mark.options(SCHEMA_CATALOG_URL="https://example.com/schemas")
    def test_resource_schema_objects_w_cache(self, rmock, mocker):
        cache_mock_set = mocker.patch.object(cache, "set")

        # fill cache
        rmock.get("https://example.com/schemas", json=ResourceSchemaMockData.get_mock_data())
        ResourceSchema.all()
        assert cache_mock_set.called

        mocker.patch.object(
            cache, "get", return_value=ResourceSchemaMockData.get_mock_data()["schemas"]
        )
        rmock.get("https://example.com/schemas", status_code=500)
        assert (
            ResourceSchemaMockData.get_all_schemas_from_mock_data(with_datapackage_info=False)
            == ResourceSchema.all()
        )
        assert rmock.call_count == 2

    @pytest.mark.options(SCHEMA_CATALOG_URL="https://example.com/schemas")
    def test_resource_schema_validation(self, rmock):
        rmock.get("https://example.com/schemas", json=ResourceSchemaMockData.get_mock_data())

        resource = ResourceFactory()

        resource.schema = Schema(name="etalab/schema-irve-statique")
        resource.validate()

        resource.schema = Schema(url="https://example.com")
        resource.validate()

        resource.schema = Schema(name="some-name", url="https://example.com")
        resource.validate()

        resource.schema = Schema(name="etalab/schema-irve-statique")
        resource.schema.clean(check_schema_in_catalog=True)

        resource.schema = Schema(url="https://example.com")
        resource.schema.clean(check_schema_in_catalog=True)

        resource.schema = Schema(name="some-name", url="https://example.com")
        resource.schema.clean(check_schema_in_catalog=True)

        # Check that no exception is raised when we do not ask for schema check for schema errors
        resource.schema = Schema(name="some-name")
        resource.validate()

        resource.schema = Schema(name="etalab/schema-irve-statique", version="1337.42.0")
        resource.validate()

        with pytest.raises(db.ValidationError):
            resource.schema = Schema(version="2.0.0")
            resource.validate()

        with pytest.raises(db.ValidationError):
            resource.schema = Schema(name="some-name")
            resource.schema.clean(check_schema_in_catalog=True)

        with pytest.raises(db.ValidationError):
            resource.schema = Schema(name="etalab/schema-irve-statique", version="1337.42.0")
            resource.schema.clean(check_schema_in_catalog=True)

        with pytest.raises(db.ValidationError):
            resource.schema = Schema(version="2.0.0")
            resource.schema.clean(check_schema_in_catalog=True)


class HarvestMetadataTest:
    def test_harvest_dataset_metadata_validate_success(self):
        dataset = DatasetFactory()

        harvest_metadata = HarvestDatasetMetadata(
            backend="DCAT",
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
            source_id="source_id",
            remote_id="remote_id",
            domain="domain.gouv.fr",
            last_update=datetime.utcnow(),
            remote_url="http://domain.gouv.fr/dataset/remote_url",
            uri="http://domain.gouv.fr/dataset/uri",
            dct_identifier="http://domain.gouv.fr/dataset/identifier",
            archived_at=datetime.utcnow(),
            archived="not-on-remote",
        )
        dataset.harvest = harvest_metadata
        dataset.save()

    def test_harvest_dataset_metadata_validation_error(self):
        harvest_metadata = HarvestDatasetMetadata(created_at="maintenant")
        dataset = DatasetFactory()
        dataset.harvest = harvest_metadata
        with pytest.raises(db.ValidationError):
            dataset.save()

    def test_harvest_dataset_metadata_no_validation_dynamic(self):
        # Adding a dynamic field (not defined in HarvestDatasetMetadata) does not raise error
        # at validation time
        harvest_metadata = HarvestDatasetMetadata(dynamic_created_at="maintenant")
        dataset = DatasetFactory()
        dataset.harvest = harvest_metadata
        dataset.save()

    def test_harvest_dataset_metadata_future_modifed_at(self):
        dataset = DatasetFactory()

        harvest_metadata = HarvestDatasetMetadata(
            created_at=datetime.utcnow(), modified_at=datetime.utcnow() + timedelta(days=1)
        )
        dataset.harvest = harvest_metadata
        dataset.save()
        assert dataset.last_modified == dataset.last_modified_internal

    def test_harvest_dataset_metadata_past_modifed_at(self):
        dataset = DatasetFactory()

        harvest_metadata = HarvestDatasetMetadata(
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
        )
        dataset.harvest = harvest_metadata
        dataset.save()
        assert dataset.last_modified == harvest_metadata.modified_at

    def test_harvest_resource_metadata_validate_success(self):
        resource = ResourceFactory()

        harvest_metadata = HarvestResourceMetadata(
            created_at=datetime.utcnow(),
            modified_at=datetime.utcnow(),
            uri="http://domain.gouv.fr/dataset/uri",
        )
        resource.harvest = harvest_metadata
        resource.validate()

    def test_harvest_resource_metadata_validation_error(self):
        harvest_metadata = HarvestResourceMetadata(created_at="maintenant")
        resource = ResourceFactory()
        resource.harvest = harvest_metadata
        with pytest.raises(db.ValidationError):
            resource.validate()

    def test_harvest_resource_metadata_no_validation_dynamic(self):
        # Adding a dynamic field (not defined in HarvestResourceMetadata) does not raise error
        # at validation time
        harvest_metadata = HarvestResourceMetadata(dynamic_created_at="maintenant")
        resource = ResourceFactory()
        resource.harvest = harvest_metadata
        resource.validate()

    def test_harvest_resource_metadata_future_modifed_at(self):
        resource = ResourceFactory()
        harvest_metadata = HarvestResourceMetadata(
            modified_at=datetime.utcnow() + timedelta(days=1)
        )
        resource.harvest = harvest_metadata
        resource.validate()

        assert resource.last_modified == resource.last_modified_internal

    def test_harvest_resource_metadata_past_modifed_at(self):
        resource = ResourceFactory()
        harvest_metadata = HarvestResourceMetadata(modified_at=datetime.utcnow())
        resource.harvest = harvest_metadata
        resource.validate()

        assert resource.last_modified == harvest_metadata.modified_at

    def test_resource_metadata_extra_modifed_at(self):
        resource = ResourceFactory(filetype="remote")
        resource.extras.update({"analysis:last-modified-at": datetime(2023, 1, 1)})
        resource.validate()

        assert resource.last_modified == resource.extras["analysis:last-modified-at"]
