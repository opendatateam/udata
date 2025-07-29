from datetime import datetime

from flask import url_for

import udata.core.organization.constants as org_constants
from udata.core.dataset.apiv2 import DEFAULT_PAGE_SIZE
from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    ResourceFactory,
)
from udata.core.dataset.models import ResourceMixin
from udata.core.organization.factories import Member, OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.models import Dataset, db
from udata.tests.api import APITestCase
from udata.tests.helpers import assert_not_emit


class DatasetAPIV2Test(APITestCase):
    def test_list_datasets(self):
        resources_a = [ResourceFactory() for _ in range(2)]
        dataset_a = DatasetFactory(title="Dataset A", resources=resources_a)

        resources_b = [ResourceFactory(format="csv") for _ in range(4)]
        dataset_b = DatasetFactory(title="Dataset B", resources=resources_b)

        response = self.get(url_for("apiv2.datasets"))
        self.assert200(response)
        data = response.json

        assert len(data["data"]) == 2
        assert data["data"][1]["title"] == dataset_a.title
        assert data["data"][0]["title"] == dataset_b.title

        assert data["data"][1]["quality"]["has_resources"]
        assert not data["data"][1]["quality"]["has_open_format"]
        assert data["data"][0]["quality"]["has_resources"]
        assert data["data"][0]["quality"]["has_open_format"]

        assert data["data"][1]["resources"]["total"] == len(resources_a)
        assert data["data"][0]["resources"]["total"] == len(resources_b)

        assert data["data"][1]["community_resources"]["total"] == 0
        assert data["data"][0]["community_resources"]["total"] == 0

    def test_filter_by_reuse(self):
        DatasetFactory(title="Dataset without reuse")

        dataset_with_reuse = DatasetFactory(title="Dataset with reuse")
        archived_dataset_with_reuse = DatasetFactory(
            title="Dataset with reuse", archived=datetime(2022, 2, 22)
        )
        reuse = ReuseFactory(datasets=[dataset_with_reuse.id, archived_dataset_with_reuse.id])

        response = self.get(url_for("apiv2.datasets", reuse=reuse.id))
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == dataset_with_reuse.title

    def test_get_dataset(self):
        resources = [ResourceFactory() for _ in range(2)]
        dataset = DatasetFactory(resources=resources)

        response = self.get(url_for("apiv2.dataset", dataset=dataset))
        self.assert200(response)
        data = response.json
        assert data["quality"]["has_resources"]
        assert data["resources"]["rel"] == "subsection"
        assert data["resources"]["href"] == url_for(
            "apiv2.resources",
            dataset=dataset.id,
            page=1,
            page_size=DEFAULT_PAGE_SIZE,
            _external=True,
        )
        assert data["resources"]["type"] == "GET"
        assert data["resources"]["total"] == len(resources)
        assert data["community_resources"]["rel"] == "subsection"
        assert data["community_resources"]["href"] == url_for(
            "api.community_resources",
            dataset=dataset.id,
            page=1,
            page_size=DEFAULT_PAGE_SIZE,
            _external=True,
        )
        assert data["community_resources"]["type"] == "GET"
        assert data["community_resources"]["total"] == 0

    def test_search_dataset(self):
        org = OrganizationFactory()
        org.add_badge(org_constants.CERTIFIED)
        org_public_service = OrganizationFactory()
        org_public_service.add_badge(org_constants.PUBLIC_SERVICE)
        _dataset_org = DatasetFactory(organization=org)
        dataset_org_public_service = DatasetFactory(organization=org_public_service)

        response = self.get(
            url_for("apiv2.dataset_search", organization_badge=org_constants.PUBLIC_SERVICE)
        )
        self.assert200(response)
        data = response.json["data"]
        assert len(data) == 1
        assert data[0]["id"] == str(dataset_org_public_service.id)

    def test_search_dataset_tags(self):
        tag_dataset_1 = DatasetFactory(tags=["my-tag-shared", "my-tag-1"])
        DatasetFactory(tags=["my-tag-shared", "my-tag-2"])

        response = self.get(url_for("apiv2.dataset_search", tag="my-tag-shared"))
        self.assert200(response)
        data = response.json["data"]
        assert len(data) == 2

        response = self.get(url_for("apiv2.dataset_search", tag=["my-tag-shared", "my-tag-1"]))
        self.assert200(response)
        data = response.json["data"]
        assert len(data) == 1
        assert data[0]["id"] == str(tag_dataset_1.id)


class DatasetResourceAPIV2Test(APITestCase):
    def test_get_specific(self):
        """Should fetch serialized resource from the API based on rid"""
        resources = [ResourceFactory() for _ in range(7)]
        specific_resource = ResourceFactory(
            id="817204ac-2202-8b4a-98e7-4284d154d10c", title="my-resource"
        )
        resources.append(specific_resource)
        dataset = DatasetFactory(resources=resources)
        response = self.get(url_for("apiv2.resource", rid=specific_resource.id))
        self.assert200(response)
        data = response.json
        assert data["dataset_id"] == str(dataset.id)
        assert data["resource"]["id"] == str(specific_resource.id)
        assert data["resource"]["title"] == specific_resource.title
        response = self.get(url_for("apiv2.resource", rid="111111ac-1111-1b1a-11e1-1111d111d11c"))
        self.assert404(response)
        com_resource = CommunityResourceFactory()
        response = self.get(url_for("apiv2.resource", rid=com_resource.id))
        self.assert200(response)
        data = response.json
        assert data["dataset_id"] is None
        assert data["resource"]["id"] == str(com_resource.id)
        assert data["resource"]["title"] == com_resource.title

    def test_get(self):
        """Should fetch 1 page of resources from the API"""
        resources = [ResourceFactory() for _ in range(7)]
        dataset = DatasetFactory(resources=resources)
        response = self.get(
            url_for("apiv2.resources", dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE)
        )
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == len(resources)
        assert data["total"] == len(resources)
        assert data["page"] == 1
        assert data["page_size"] == DEFAULT_PAGE_SIZE
        assert data["next_page"] is None
        assert data["previous_page"] is None

    def test_get_missing_param(self):
        """Should fetch 1 page of resources from the API using its default parameters"""
        resources = [ResourceFactory() for _ in range(7)]
        dataset = DatasetFactory(resources=resources)
        response = self.get(url_for("apiv2.resources", dataset=dataset.id))
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == len(resources)
        assert data["total"] == len(resources)
        assert data["page"] == 1
        assert data["page_size"] == DEFAULT_PAGE_SIZE
        assert data["next_page"] is None
        assert data["previous_page"] is None

    def test_get_next_page(self):
        """Should fetch 2 pages of resources from the API"""
        resources = [ResourceFactory() for _ in range(80)]
        dataset = DatasetFactory(resources=resources)
        response = self.get(
            url_for("apiv2.resources", dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE)
        )
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == DEFAULT_PAGE_SIZE
        assert data["total"] == len(resources)
        assert data["page"] == 1
        assert data["page_size"] == DEFAULT_PAGE_SIZE
        assert data["next_page"] == url_for(
            "apiv2.resources",
            dataset=dataset.id,
            page=2,
            page_size=DEFAULT_PAGE_SIZE,
            _external=True,
        )
        assert data["previous_page"] is None

        response = self.get(data["next_page"])
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == len(resources) - DEFAULT_PAGE_SIZE
        assert data["total"] == len(resources)
        assert data["page"] == 2
        assert data["page_size"] == DEFAULT_PAGE_SIZE
        assert data["next_page"] is None
        assert data["previous_page"] == url_for(
            "apiv2.resources",
            dataset=dataset.id,
            page=1,
            page_size=DEFAULT_PAGE_SIZE,
            _external=True,
        )

    def test_get_specific_type(self):
        """Should fetch resources of type main from the API"""
        nb_resources__of_specific_type = 80
        resources = [ResourceFactory() for _ in range(40)]
        resources += [ResourceFactory(type="main") for _ in range(nb_resources__of_specific_type)]
        dataset = DatasetFactory(resources=resources)
        # Try without resource type filter
        response = self.get(
            url_for("apiv2.resources", dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE)
        )
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == DEFAULT_PAGE_SIZE
        assert data["total"] == len(resources)
        assert data["page"] == 1
        assert data["page_size"] == DEFAULT_PAGE_SIZE
        assert data["next_page"] == url_for(
            "apiv2.resources",
            dataset=dataset.id,
            page=2,
            page_size=DEFAULT_PAGE_SIZE,
            _external=True,
        )
        assert data["previous_page"] is None

        # Try with resource type filter
        response = self.get(
            url_for(
                "apiv2.resources",
                dataset=dataset.id,
                page=1,
                page_size=DEFAULT_PAGE_SIZE,
                type="main",
            )
        )
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == DEFAULT_PAGE_SIZE
        assert data["total"] == nb_resources__of_specific_type
        assert data["page"] == 1
        assert data["page_size"] == DEFAULT_PAGE_SIZE
        assert data["next_page"] == url_for(
            "apiv2.resources",
            dataset=dataset.id,
            page=2,
            page_size=DEFAULT_PAGE_SIZE,
            type="main",
            _external=True,
        )
        assert data["previous_page"] is None

        response = self.get(data["next_page"])
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == nb_resources__of_specific_type - DEFAULT_PAGE_SIZE
        assert data["total"] == nb_resources__of_specific_type
        assert data["page"] == 2
        assert data["page_size"] == DEFAULT_PAGE_SIZE
        assert data["next_page"] is None
        assert data["previous_page"] == url_for(
            "apiv2.resources",
            dataset=dataset.id,
            page=1,
            page_size=DEFAULT_PAGE_SIZE,
            type="main",
            _external=True,
        )

    def test_get_with_query_string(self):
        """Should fetch resources according to query string from the API"""
        nb_resources_with_specific_title = 20
        resources = [ResourceFactory() for _ in range(40)]
        for i in range(nb_resources_with_specific_title):
            resources += [
                ResourceFactory(title="primary-{0}".format(i))
                if i % 2
                else ResourceFactory(title="secondary-{0}".format(i))
            ]
        dataset = DatasetFactory(resources=resources)

        # Try without query string filter
        response = self.get(
            url_for("apiv2.resources", dataset=dataset.id, page=1, page_size=DEFAULT_PAGE_SIZE)
        )
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == DEFAULT_PAGE_SIZE
        assert data["total"] == len(resources)
        assert data["page"] == 1
        assert data["page_size"] == DEFAULT_PAGE_SIZE
        assert data["next_page"] == url_for(
            "apiv2.resources",
            dataset=dataset.id,
            page=2,
            page_size=DEFAULT_PAGE_SIZE,
            _external=True,
        )
        assert data["previous_page"] is None

        # Try with query string filter
        response = self.get(
            url_for(
                "apiv2.resources",
                dataset=dataset.id,
                page=1,
                page_size=DEFAULT_PAGE_SIZE,
                q="primary",
            )
        )
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == 10
        assert data["total"] == 10
        assert data["page"] == 1
        assert data["page_size"] == DEFAULT_PAGE_SIZE
        assert data["next_page"] is None
        assert data["previous_page"] is None

        # Try with query string filter to check case-insensitivity
        response = self.get(
            url_for(
                "apiv2.resources",
                dataset=dataset.id,
                page=1,
                page_size=DEFAULT_PAGE_SIZE,
                q="PriMarY",
            )
        )
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == 10
        assert data["total"] == 10
        assert data["page"] == 1
        assert data["page_size"] == DEFAULT_PAGE_SIZE
        assert data["next_page"] is None
        assert data["previous_page"] is None


class DatasetExtrasAPITest(APITestCase):
    modules = None

    def setUp(self):
        self.login()
        self.dataset = DatasetFactory(owner=self.user)

    def test_get_dataset_extras(self):
        Dataset.extras.register("check::date", db.DateTimeField)
        self.dataset.extras = {
            "test::extra": "test-value",
            "check::date": datetime.fromisoformat("2024-04-14 08:42:00"),
        }
        self.dataset.save()
        response = self.get(url_for("apiv2.dataset_extras", dataset=self.dataset))
        self.assert200(response)
        data = response.json
        assert data["test::extra"] == "test-value"
        assert data["check::date"] == "2024-04-14T08:42:00"

    def test_update_dataset_extras(self):
        self.dataset.extras = {
            "test::extra": "test-value",
            "test::extra-second": "test-value-second",
            "test::none-will-be-deleted": "test-value",
        }
        self.dataset.save()

        data = ["test::extra-second", "another::key"]
        response = self.put(url_for("apiv2.dataset_extras", dataset=self.dataset), data)
        self.assert400(response)
        assert response.json["message"] == "Wrong payload format, dict expected"

        data = {
            "test::extra-second": "test-value-changed",
            "another::key": "another-value",
            "test::none": None,
            "test::none-will-be-deleted": None,
        }

        # We don't expect post save signals on extras update
        unexpected_signals = Dataset.after_save, Dataset.on_update
        with assert_not_emit(*unexpected_signals):
            response = self.put(url_for("apiv2.dataset_extras", dataset=self.dataset), data)
        self.assert200(response)

        self.dataset.reload()
        assert self.dataset.extras["test::extra"] == "test-value"
        assert self.dataset.extras["test::extra-second"] == "test-value-changed"
        assert self.dataset.extras["another::key"] == "another-value"
        assert "test::none" not in self.dataset.extras
        assert "test::none-will-be-deleted" not in self.dataset.extras

    def test_delete_dataset_extras(self):
        self.dataset.extras = {"test::extra": "test-value", "another::key": "another-value"}
        self.dataset.save()

        data = {"another::key": "another-value"}
        response = self.delete(url_for("apiv2.dataset_extras", dataset=self.dataset), data)
        self.assert400(response)
        assert response.json["message"] == "Wrong payload format, list expected"

        data = ["another::key"]

        # We don't expect post save signals on extras update
        unexpected_signals = Dataset.after_save, Dataset.on_update
        with assert_not_emit(*unexpected_signals):
            response = self.delete(url_for("apiv2.dataset_extras", dataset=self.dataset), data)
        self.assert204(response)

        self.dataset.reload()
        assert len(self.dataset.extras) == 1
        assert self.dataset.extras["test::extra"] == "test-value"

    def test_dataset_custom_extras_str(self):
        member = Member(user=self.user, role="admin")
        org = OrganizationFactory(members=[member])
        org.extras = {
            "custom": [
                {
                    "title": "color",
                    "description": "the banner color of the dataset (Hex code)",
                    "type": "str",
                }
            ]
        }
        org.save()
        dataset = DatasetFactory(organization=org)

        data = {"custom:test": "FFFFFFF"}
        response = self.put(url_for("apiv2.dataset_extras", dataset=dataset), data)
        self.assert400(response)
        assert (
            "Dataset's organization did not define the requested custom metadata"
            in response.json["message"]
        )

        data = {"custom:color": 123}
        response = self.put(url_for("apiv2.dataset_extras", dataset=dataset), data)
        self.assert400(response)
        assert "Custom metadata is not of the right type" in response.json["message"]

        data = {"custom:color": "FFFFFFF"}
        response = self.put(url_for("apiv2.dataset_extras", dataset=dataset), data)
        self.assert200(response)
        dataset.reload()
        assert dataset.extras["custom:color"] == "FFFFFFF"

    def test_dataset_custom_extras_choices(self):
        member = Member(user=self.user, role="admin")
        org = OrganizationFactory(members=[member])
        org.extras = {
            "custom": [
                {
                    "title": "color",
                    "description": "the colors of the dataset (Hex code)",
                    "type": "choice",
                    "choices": ["yellow", "blue"],
                }
            ]
        }
        org.save()
        dataset = DatasetFactory(organization=org)

        data = {"custom:color": "FFFFFFF"}
        response = self.put(url_for("apiv2.dataset_extras", dataset=dataset), data)
        self.assert400(response)
        assert "Custom metadata choice is not defined by organization" in response.json["message"]

        data = {"custom:color": "yellow"}
        response = self.put(url_for("apiv2.dataset_extras", dataset=dataset), data)
        self.assert200(response)
        dataset.reload()
        assert dataset.extras["custom:color"] == "yellow"


class DatasetResourceExtrasAPITest(APITestCase):
    modules = None

    def setUp(self):
        self.login()
        self.dataset = DatasetFactory(owner=self.user)

    def test_get_ressource_extras(self):
        """It should fetch a resource from the API"""
        ResourceMixin.extras.register("check:date", db.DateTimeField)

        resource = ResourceFactory()
        resource.extras = {
            "test::extra": "test-value",
            "check:date": datetime(2023, 4, 20, 13, 57, 31, 289000),
        }
        self.dataset.resources.append(resource)
        self.dataset.save()
        response = self.get(url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id))
        self.assert200(response)
        data = response.json
        assert data["test::extra"] == "test-value"
        assert data["check:date"] == "2023-04-20T13:57:31.289000"

    def test_update_resource_extras(self):
        resource = ResourceFactory()
        resource.extras = {
            "test::extra": "test-value",
            "test::extra-second": "test-value-second",
            "test::none-will-be-deleted": "test-value",
        }
        self.dataset.resources.append(resource)
        self.dataset.save()

        data = ["test::extra-second", "another::key"]
        response = self.put(
            url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id), data
        )
        self.assert400(response)
        assert response.json["message"] == "Wrong payload format, dict expected"

        data = {
            "test::extra-second": "test-value-changed",
            "another::key": "another-value",
            "test::none": None,
            "test::none-will-be-deleted": None,
        }
        # We don't expect post save signals on extras update
        unexpected_signals = Dataset.after_save, Dataset.on_update
        with assert_not_emit(*unexpected_signals):
            response = self.put(
                url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id), data
            )
        self.assert200(response)

        self.dataset.reload()
        assert self.dataset.resources[0].extras["test::extra"] == "test-value"
        assert self.dataset.resources[0].extras["test::extra-second"] == "test-value-changed"
        assert self.dataset.resources[0].extras["another::key"] == "another-value"
        assert "test::none" not in self.dataset.resources[0].extras
        assert "test::none-will-be-deleted" not in self.dataset.resources[0].extras

    def test_delete_resource_extras(self):
        resource = ResourceFactory()
        resource.extras = {"test::extra": "test-value", "another::key": "another-value"}
        self.dataset.resources.append(resource)
        self.dataset.save()

        data = {"another::key": "another-value"}
        response = self.delete(
            url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id), data
        )
        self.assert400(response)
        assert response.json["message"] == "Wrong payload format, list expected"

        data = ["another::key"]
        # We don't expect post save signals on extras update
        unexpected_signals = Dataset.after_save, Dataset.on_update
        with assert_not_emit(*unexpected_signals):
            response = self.delete(
                url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id), data
            )
        self.assert204(response)
        self.dataset.reload()
        assert len(self.dataset.resources[0].extras) == 1
        assert self.dataset.resources[0].extras["test::extra"] == "test-value"
