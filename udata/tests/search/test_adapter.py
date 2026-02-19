import datetime
from unittest.mock import patch

import pytest
from flask_restx import inputs
from flask_restx.reqparse import RequestParser

from udata import search
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.search import DataserviceSearch
from udata.core.dataset.factories import (
    DatasetFactory,
    HiddenDatasetFactory,
    ResourceFactory,
)
from udata.core.dataset.models import Schema
from udata.core.dataset.search import DatasetSearch
from udata.core.organization.constants import (
    ASSOCIATION,
    COMPANY,
    LOCAL_AUTHORITY,
    NOT_SPECIFIED,
    PUBLIC_SERVICE,
    USER,
)
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.reuse.search import ReuseSearch
from udata.core.topic.factories import TopicElementDatasetFactory, TopicFactory
from udata.core.user.factories import UserFactory
from udata.i18n import gettext as _
from udata.search import as_task_param, reindex
from udata.search.commands import index_model
from udata.tests.api import APITestCase
from udata.utils import clean_string

from . import FakeSearch

#############################################################################
#                  Custom search adapters and metrics                       #
#############################################################################

RANGE_LABELS = {
    "none": _("Never reused"),
    "little": _("Little reused"),
    "quite": _("Quite reused"),
    "heavy": _("Heavily reused"),
}


class FakeSearchWithBool(FakeSearch):
    filters = {"boolean": search.BoolFilter()}


class FakeSearchWithCoverage(FakeSearch):
    filters = {"coverage": search.TemporalCoverageFilter()}


#############################################################################
#                                 Helpers                                   #
#############################################################################


def assertHasArgument(parser, name, _type, choices=None):
    __tracebackhide__ = True
    candidates = [arg for arg in parser.args if arg.name == name]
    assert len(candidates) == 1, "Should have strictly one argument"
    arg = candidates[0]
    assert arg.type == _type
    assert not arg.required
    if choices:
        assert set(arg.choices) == set(choices)


#############################################################################
#                                  Tests                                    #
#############################################################################


class SearchAdaptorTest:
    def test_as_request_parser_filter(self):
        parser = FakeSearch.as_request_parser()
        assert isinstance(parser, RequestParser)

        # query + tag and other filters + sorts + pagination
        assert len(parser.args) == 6
        assertHasArgument(parser, "q", str)
        assertHasArgument(parser, "sort", str)
        assertHasArgument(parser, "tag", clean_string)
        assertHasArgument(parser, "other", clean_string)
        assertHasArgument(parser, "page", int)
        assertHasArgument(parser, "page_size", int)

    def test_as_request_parser_bool_filter(self):
        parser = FakeSearchWithBool.as_request_parser()
        assert isinstance(parser, RequestParser)

        # query + boolean filter + sorts + pagination
        assert len(parser.args) == 5
        assertHasArgument(parser, "q", str)
        assertHasArgument(parser, "sort", str)
        assertHasArgument(parser, "boolean", inputs.boolean)
        assertHasArgument(parser, "page", int)
        assertHasArgument(parser, "page_size", int)

    def test_as_request_parser_temporal_coverage_facet(self):
        parser = FakeSearchWithCoverage.as_request_parser()
        filter = FakeSearchWithCoverage.filters["coverage"]
        assert isinstance(parser, RequestParser)

        # query + range facet + sorts + pagination
        assert len(parser.args) == 5
        assertHasArgument(parser, "q", str)
        assertHasArgument(parser, "sort", str)
        assertHasArgument(parser, "coverage", filter.validate_parameter)
        assertHasArgument(parser, "page", int)
        assertHasArgument(parser, "page_size", int)


@pytest.mark.options(ELASTICSEARCH_URL="http://localhost:9200")
class IndexingLifecycleTest(APITestCase):
    @patch("udata.search.get_elastic_client")
    def test_reindex_calls_delete_one_if_not_indexable(self, mock_get_client):
        fake_data = HiddenDatasetFactory(id="61fd30cb29ea95c7bc0e1211")

        with patch.object(DatasetSearch, "service_class") as mock_service_class:
            mock_service = mock_service_class.return_value
            reindex.run(*as_task_param(fake_data))
            mock_service.delete_one.assert_called_once_with(str(fake_data.id))

    @patch("udata.search.get_elastic_client")
    def test_reindex_calls_feed_if_indexable(self, mock_get_client):
        resource = ResourceFactory(schema=Schema(url="http://localhost/my-schema"))
        fake_data = DatasetFactory(id="61fd30cb29ea95c7bc0e1211", resources=[resource])

        with patch.object(DatasetSearch, "service_class") as mock_service_class:
            mock_service = mock_service_class.return_value
            reindex.run(*as_task_param(fake_data))
            mock_service.feed.assert_called_once()

    @patch("udata.search.commands.get_elastic_client")
    def test_index_model(self, mock_get_client):
        DatasetFactory(id="61fd30cb29ea95c7bc0e1211")

        with patch.object(DatasetSearch, "service_class") as mock_service_class:
            mock_service = mock_service_class.return_value
            index_model(DatasetSearch, start=None, reindex=False, from_datetime=None)
            mock_service.feed.assert_called_once()

    @patch("udata.search.commands.get_elastic_client")
    def test_reindex_model_creates_index_and_feeds(self, mock_get_client):
        DatasetFactory(id="61fd30cb29ea95c7bc0e1211")
        mock_es = mock_get_client.return_value.es

        with patch.object(DatasetSearch, "service_class") as mock_service_class:
            mock_service = mock_service_class.return_value
            index_model(DatasetSearch, start=datetime.datetime(2022, 2, 20, 20, 2), reindex=True)
            mock_es.indices.create.assert_called_once()
            mock_service.feed.assert_called_once()

    @patch("udata.search.commands.get_elastic_client")
    def test_index_model_from_datetime(self, mock_get_client):
        DatasetFactory(
            id="61fd30cb29ea95c7bc0e1211", last_modified_internal=datetime.datetime(2020, 1, 1)
        )
        DatasetFactory(
            id="61fd30cb29ea95c7bc0e1212", last_modified_internal=datetime.datetime(2022, 1, 1)
        )

        with patch.object(DatasetSearch, "service_class") as mock_service_class:
            mock_service = mock_service_class.return_value
            index_model(DatasetSearch, start=None, from_datetime=datetime.datetime(2023, 1, 1))
            mock_service.feed.assert_not_called()

        with patch.object(DatasetSearch, "service_class") as mock_service_class:
            mock_service = mock_service_class.return_value
            index_model(DatasetSearch, start=None, from_datetime=datetime.datetime(2021, 1, 1))
            mock_service.feed.assert_called_once()


class DatasetSearchAdapterTest(APITestCase):
    def test_serialize_includes_topic_ids(self):
        """Test that DatasetSearch.serialize includes topic_ids in the serialized document"""
        dataset = DatasetFactory()
        topic1 = TopicFactory()
        topic2 = TopicFactory()

        TopicElementDatasetFactory(element=dataset, topic=topic1)
        TopicElementDatasetFactory(element=dataset, topic=topic2)

        serialized = DatasetSearch.serialize(dataset)

        assert "topics" in serialized
        assert len(serialized["topics"]) == 2
        assert str(topic1.id) in serialized["topics"]
        assert str(topic2.id) in serialized["topics"]

    def test_serialize_empty_topics_for_dataset_without_topics(self):
        """Test that DatasetSearch.serialize returns empty topics list for dataset without topics"""
        dataset = DatasetFactory()

        serialized = DatasetSearch.serialize(dataset)

        assert "topics" in serialized
        assert serialized["topics"] == []

    def test_serialize_deduplicates_topic_ids(self):
        """Test that DatasetSearch.serialize deduplicates topic IDs when same topic appears multiple times"""
        dataset = DatasetFactory()
        topic = TopicFactory()

        # Create multiple topic elements for the same topic
        TopicElementDatasetFactory(element=dataset, topic=topic)
        TopicElementDatasetFactory(element=dataset, topic=topic)

        serialized = DatasetSearch.serialize(dataset)

        assert "topics" in serialized
        assert len(serialized["topics"]) == 1
        assert str(topic.id) in serialized["topics"]

    def test_serialize_includes_access_type(self):
        """Test that DatasetSearch.serialize includes access_type in the serialized document"""
        from udata.core.access_type.constants import AccessType

        dataset = DatasetFactory(access_type=AccessType.OPEN)
        serialized = DatasetSearch.serialize(dataset)

        assert "access_type" in serialized
        assert serialized["access_type"] == "open"

    def test_serialize_includes_format_family_tabular(self):
        """Test that DatasetSearch.serialize includes format_family for tabular formats"""
        resource_csv = ResourceFactory(format="csv")
        resource_xlsx = ResourceFactory(format="xlsx")
        dataset = DatasetFactory(resources=[resource_csv, resource_xlsx])

        serialized = DatasetSearch.serialize(dataset)

        assert "format_family" in serialized
        assert serialized["format_family"] == ["tabular"]

    def test_serialize_includes_format_family_machine_readable(self):
        """Test that DatasetSearch.serialize includes format_family for machine-readable formats"""
        resource_json = ResourceFactory(format="json")
        resource_xml = ResourceFactory(format="xml")
        dataset = DatasetFactory(resources=[resource_json, resource_xml])

        serialized = DatasetSearch.serialize(dataset)

        assert "format_family" in serialized
        assert serialized["format_family"] == ["machine_readable"]

    def test_serialize_includes_format_family_geographical(self):
        """Test that DatasetSearch.serialize includes format_family for geographical formats"""
        resource_shp = ResourceFactory(format="shp")
        resource_geojson = ResourceFactory(format="geojson")
        dataset = DatasetFactory(resources=[resource_shp, resource_geojson])

        serialized = DatasetSearch.serialize(dataset)

        assert "format_family" in serialized
        assert serialized["format_family"] == ["geographical"]

    def test_serialize_includes_format_family_documents_for_pdf(self):
        """Test that DatasetSearch.serialize returns 'documents' for PDF format"""
        resource_pdf = ResourceFactory(format="pdf")
        dataset = DatasetFactory(resources=[resource_pdf])

        serialized = DatasetSearch.serialize(dataset)

        assert "format_family" in serialized
        assert serialized["format_family"] == ["documents"]

    def test_serialize_includes_format_family_other_for_no_resources(self):
        """Test that DatasetSearch.serialize returns 'other' for datasets without resources"""
        dataset = DatasetFactory(resources=[])

        serialized = DatasetSearch.serialize(dataset)

        assert "format_family" in serialized
        assert serialized["format_family"] == ["other"]

    def test_serialize_includes_format_family_mixed(self):
        """Test that DatasetSearch.serialize includes multiple format families when mixed"""
        resource_csv = ResourceFactory(format="csv")
        resource_json = ResourceFactory(format="json")
        resource_pdf = ResourceFactory(format="pdf")
        resource_shp = ResourceFactory(format="shp")
        dataset = DatasetFactory(
            resources=[resource_csv, resource_json, resource_pdf, resource_shp]
        )

        serialized = DatasetSearch.serialize(dataset)

        assert "format_family" in serialized
        assert set(serialized["format_family"]) == {
            "tabular",
            "machine_readable",
            "geographical",
            "documents",
        }

    def test_serialize_includes_producer_type_public_service(self):
        """Test that DatasetSearch.serialize includes producer_type for public-service orgs"""
        org = OrganizationFactory()
        org.add_badge(PUBLIC_SERVICE)
        dataset = DatasetFactory(organization=org)

        serialized = DatasetSearch.serialize(dataset)

        assert "producer_type" in serialized
        assert PUBLIC_SERVICE in serialized["producer_type"]

    def test_serialize_includes_producer_type_local_authority(self):
        """Test that DatasetSearch.serialize includes producer_type for local-authority orgs"""
        org = OrganizationFactory()
        org.add_badge(LOCAL_AUTHORITY)
        dataset = DatasetFactory(organization=org)

        serialized = DatasetSearch.serialize(dataset)

        assert "producer_type" in serialized
        assert LOCAL_AUTHORITY in serialized["producer_type"]

    def test_serialize_includes_producer_type_association(self):
        """Test that DatasetSearch.serialize includes producer_type for association orgs"""
        org = OrganizationFactory()
        org.add_badge(ASSOCIATION)
        dataset = DatasetFactory(organization=org)

        serialized = DatasetSearch.serialize(dataset)

        assert "producer_type" in serialized
        assert ASSOCIATION in serialized["producer_type"]

    def test_serialize_includes_producer_type_company(self):
        """Test that DatasetSearch.serialize includes producer_type for company orgs"""
        org = OrganizationFactory()
        org.add_badge(COMPANY)
        dataset = DatasetFactory(organization=org)

        serialized = DatasetSearch.serialize(dataset)

        assert "producer_type" in serialized
        assert COMPANY in serialized["producer_type"]

    def test_serialize_includes_producer_type_user(self):
        """Test that DatasetSearch.serialize includes 'user' for datasets owned by users"""
        user = UserFactory()
        dataset = DatasetFactory(owner=user, organization=None)

        serialized = DatasetSearch.serialize(dataset)

        assert "producer_type" in serialized
        assert serialized["producer_type"] == [USER]

    def test_serialize_excludes_certified_from_producer_type(self):
        """Test that certified badge is excluded from producer_type"""
        from udata.core.organization.constants import CERTIFIED

        org = OrganizationFactory()
        org.add_badge(PUBLIC_SERVICE)
        org.add_badge(CERTIFIED)
        dataset = DatasetFactory(organization=org)

        serialized = DatasetSearch.serialize(dataset)

        assert "producer_type" in serialized
        assert PUBLIC_SERVICE in serialized["producer_type"]
        assert CERTIFIED not in serialized["producer_type"]

    def test_serialize_includes_multiple_producer_types(self):
        """Test that DatasetSearch.serialize includes multiple producer_types"""
        org = OrganizationFactory()
        org.add_badge(PUBLIC_SERVICE)
        org.add_badge(LOCAL_AUTHORITY)
        dataset = DatasetFactory(organization=org)

        serialized = DatasetSearch.serialize(dataset)

        assert "producer_type" in serialized
        assert set(serialized["producer_type"]) == {PUBLIC_SERVICE, LOCAL_AUTHORITY}

    def test_serialize_not_specified_producer_type_for_org_without_badges(self):
        """Test that DatasetSearch.serialize returns 'not-specified' for orgs without producer badges"""
        org = OrganizationFactory()
        dataset = DatasetFactory(organization=org)

        serialized = DatasetSearch.serialize(dataset)

        assert "producer_type" in serialized
        assert serialized["producer_type"] == [NOT_SPECIFIED]


class ReuseSearchAdapterTest(APITestCase):
    def test_serialize_includes_producer_type_public_service(self):
        """Test that ReuseSearch.serialize includes producer_type for public-service orgs"""
        org = OrganizationFactory()
        org.add_badge(PUBLIC_SERVICE)
        reuse = ReuseFactory(organization=org)

        serialized = ReuseSearch.serialize(reuse)

        assert "producer_type" in serialized
        assert PUBLIC_SERVICE in serialized["producer_type"]

    def test_serialize_includes_producer_type_user(self):
        """Test that ReuseSearch.serialize includes 'user' for reuses owned by users"""
        user = UserFactory()
        reuse = ReuseFactory(owner=user, organization=None)

        serialized = ReuseSearch.serialize(reuse)

        assert "producer_type" in serialized
        assert serialized["producer_type"] == [USER]


class DataserviceSearchAdapterTest(APITestCase):
    def test_serialize_includes_access_type(self):
        """Test that DataserviceSearch.serialize includes access_type in the serialized document"""
        from udata.core.access_type.constants import AccessType

        dataservice = DataserviceFactory(access_type=AccessType.OPEN)
        serialized = DataserviceSearch.serialize(dataservice)

        assert "access_type" in serialized
        assert serialized["access_type"] == "open"

    def test_serialize_includes_producer_type_public_service(self):
        """Test that DataserviceSearch.serialize includes producer_type for public-service orgs"""
        org = OrganizationFactory()
        org.add_badge(PUBLIC_SERVICE)
        dataservice = DataserviceFactory(organization=org)

        serialized = DataserviceSearch.serialize(dataservice)

        assert "producer_type" in serialized
        assert PUBLIC_SERVICE in serialized["producer_type"]

    def test_serialize_includes_producer_type_user(self):
        """Test that DataserviceSearch.serialize includes 'user' for dataservices owned by users"""
        user = UserFactory()
        dataservice = DataserviceFactory(owner=user, organization=None)

        serialized = DataserviceSearch.serialize(dataservice)

        assert "producer_type" in serialized
        assert serialized["producer_type"] == [USER]
