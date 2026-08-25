from datetime import UTC, datetime

from flask import url_for
from mongoengine.context_managers import query_counter
from mongoengine.fields import DateTimeField

import udata.core.organization.constants as org_constants
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.api import DatasetApiParser
from udata.core.dataset.apiv2 import DEFAULT_PAGE_SIZE
from udata.core.dataset.constants import UpdateFrequency
from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    ResourceFactory,
)
from udata.core.dataset.models import ResourceMixin
from udata.core.organization.factories import Member, OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.storages import images
from udata.core.user.factories import AdminFactory, UserFactory
from udata.models import Dataset
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

    def test_list_invalid_pagination_params_return_400(self):
        """The shared positive page/page_size validation also guards list endpoints."""
        DatasetFactory()
        for params in ({"page_size": -1}, {"page_size": 0}, {"page": 0}, {"page": -1}):
            response = self.get(url_for("apiv2.datasets", **params))
            self.assert400(response)

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

    def test_filter_by_dataservice(self):
        DatasetFactory(title="Dataset without dataservice")

        dataset_with_dataservice = DatasetFactory(title="Dataset with dataservice")
        archived_dataset_with_dataservice = DatasetFactory(
            title="Dataset with dataservice", archived=datetime(2022, 2, 22)
        )
        dataservice = DataserviceFactory(
            datasets=[dataset_with_dataservice.id, archived_dataset_with_dataservice.id]
        )

        response = self.get(url_for("apiv2.datasets", dataservice=dataservice.id))
        self.assert200(response)
        data = response.json
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == dataset_with_dataservice.title

    def test_filter_by_reuse_does_not_dereference_datasets(self):
        # Regression: filtering datasets by reuse used to dereference the whole
        # reuse.datasets list, loading every referenced Dataset with its embedded
        # resources (megabytes for a dataset with thousands of resources) just to
        # read their ids. Building the filter must hit the database exactly once
        # (fetch the reuse's references), never dereferencing the datasets.
        dataset = DatasetFactory(resources=[ResourceFactory() for _ in range(20)])
        reuse = ReuseFactory(datasets=[dataset.id])

        with query_counter() as counter:
            DatasetApiParser.parse_filters(Dataset.objects, {"reuse": str(reuse.id)})
            assert counter == 1

    def test_filter_by_dataservice_does_not_dereference_datasets(self):
        dataset = DatasetFactory(resources=[ResourceFactory() for _ in range(20)])
        dataservice = DataserviceFactory(datasets=[dataset.id])

        with query_counter() as counter:
            DatasetApiParser.parse_filters(Dataset.objects, {"dataservice": str(dataservice.id)})
            assert counter == 1

    def test_filter_by_reuse_does_not_copy_the_image_storage(self):
        # Regression: mongoengine deep-copies the document's fields when
        # auto-dereferencing is off, and `Reuse.image` is an ImageField holding
        # the image storage, hence its backend. On the S3 backend that backend
        # owns boto3 clients, which recurse until RecursionError when copied.
        dataset = DatasetFactory(title="Dataset with reuse")
        reuse = ReuseFactory(datasets=[dataset.id])

        class UncopyableBackend:
            def __deepcopy__(self, memo):
                raise AssertionError("the image storage backend must not be copied")

        original_backend = images.backend
        images.backend = UncopyableBackend()
        try:
            response = self.get(url_for("apiv2.datasets", reuse=reuse.id))
        finally:
            images.backend = original_backend

        self.assert200(response)
        assert [d["id"] for d in response.json["data"]] == [str(dataset.id)]

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

    def test_search_dataset_badges(self):
        test_dataset = DatasetFactory(badges=[{"kind": "spd"}, {"kind": "hvd"}])
        DatasetFactory(badges=[{"kind": "spd"}, {"kind": "inspire"}])

        response = self.get(url_for("apiv2.dataset_search", badge="spd"))
        self.assert200(response)
        data = response.json["data"]
        assert len(data) == 2

        response = self.get(url_for("apiv2.dataset_search", badge="hvd"))
        self.assert200(response)
        data = response.json["data"]
        assert len(data) == 1
        assert data[0]["id"] == str(test_dataset.id)


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

    def test_get_with_query_string_special_chars(self):
        """The query string is matched as a literal substring, not as a regex"""
        resources = [
            ResourceFactory(title="Total (2024)"),
            ResourceFactory(title="Total 2024"),
        ]
        dataset = DatasetFactory(resources=resources)
        response = self.get(url_for("apiv2.resources", dataset=dataset.id, q="(2024)"))
        self.assert200(response)
        data = response.json
        # A naive regex would treat "(2024)" as a group and match both titles
        assert data["total"] == 1
        assert data["data"][0]["title"] == "Total (2024)"

    def test_get_with_type_and_query_string(self):
        """The type and query string filters combine (AND)"""
        resources = [
            ResourceFactory(type="main", title="alpha report"),
            ResourceFactory(type="main", title="beta report"),
            ResourceFactory(type="documentation", title="alpha doc"),
        ]
        dataset = DatasetFactory(resources=resources)
        response = self.get(url_for("apiv2.resources", dataset=dataset.id, type="main", q="alpha"))
        self.assert200(response)
        data = response.json
        assert data["total"] == 1
        assert data["data"][0]["title"] == "alpha report"

    def test_invalid_pagination_params_return_400(self):
        """Out-of-range page/page_size must be rejected with a 400.

        A non-positive ``page_size`` used to reach the ``$slice`` aggregation as a
        negative length and crash with a 500 (OperationFailure: "Third argument to
        $slice must be positive").
        """
        dataset = DatasetFactory(resources=[ResourceFactory() for _ in range(3)])
        for params in ({"page_size": -1}, {"page_size": 0}, {"page": 0}, {"page": -1}):
            response = self.get(url_for("apiv2.resources", dataset=dataset.id, **params))
            self.assert400(response)


class DatasetExtrasAPITest(APITestCase):
    def setUp(self):
        self.login()
        self.dataset = DatasetFactory(owner=self.user)

    def test_get_dataset_extras(self):
        Dataset.extras.register("check::date", DateTimeField)
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

    def test_update_dataset_extras_without_permission(self):
        """It should return a 403 when the user cannot edit the dataset"""
        someone_else_dataset = DatasetFactory(owner=UserFactory())

        response = self.put(
            url_for("apiv2.dataset_extras", dataset=someone_else_dataset),
            {"test::extra": "test-value"},
        )

        self.assert403(response)
        assert "message" in response.json
        someone_else_dataset.reload()
        assert "test::extra" not in someone_else_dataset.extras

    def test_delete_dataset_extras_without_permission(self):
        """It should return a 403 when the user cannot delete the dataset extras"""
        someone_else_dataset = DatasetFactory(owner=UserFactory())
        someone_else_dataset.extras = {"test::extra": "test-value"}
        someone_else_dataset.save()

        response = self.delete(
            url_for("apiv2.dataset_extras", dataset=someone_else_dataset), ["test::extra"]
        )

        self.assert403(response)
        assert "message" in response.json
        someone_else_dataset.reload()
        assert someone_else_dataset.extras["test::extra"] == "test-value"

    def test_update_dataset_extras_rejects_reserved_key_for_non_admin(self):
        # transport:url is written by the transport.data.gouv.fr integration and
        # trusted by the frontend. Every key of this payload is an explicit write
        # intent, so a reserved one is rejected rather than dropped: answering 200
        # would tell a platform service its write went through when it did not.
        response = self.put(
            url_for("apiv2.dataset_extras", dataset=self.dataset),
            {"transport:url": "https://transport.data.gouv.fr/x"},
        )
        self.assert400(response)
        assert "transport:url" in response.json["message"]
        self.dataset.reload()
        assert "transport:url" not in self.dataset.extras

    def test_update_dataset_extras_rejects_reserved_key_deletion_by_null(self):
        # A null value deletes the key, so it is a third write vector alongside the
        # PUT and the DELETE, and it must be rejected just the same.
        self.dataset.extras = {"transport:url": "https://transport.data.gouv.fr/x"}
        self.dataset.save()

        self.assert400(
            self.put(url_for("apiv2.dataset_extras", dataset=self.dataset), {"transport:url": None})
        )

        self.dataset.reload()
        assert self.dataset.extras["transport:url"] == "https://transport.data.gouv.fr/x"

    def test_delete_dataset_extras_rejects_reserved_key_for_non_admin(self):
        # Symmetric to the PUT case: a regular user must not be able to wipe a
        # platform-written extra either.
        self.dataset.extras = {"transport:url": "https://transport.data.gouv.fr/x"}
        self.dataset.save()

        self.assert400(
            self.delete(url_for("apiv2.dataset_extras", dataset=self.dataset), ["transport:url"])
        )

        self.dataset.reload()
        assert self.dataset.extras["transport:url"] == "https://transport.data.gouv.fr/x"

    def test_delete_dataset_extras_rejects_non_string_key(self):
        # The payload is a raw JSON list, so its elements are arbitrary values:
        # a non-string must be a 400, not a crash in the reserved-key matching.
        self.assert400(self.delete(url_for("apiv2.dataset_extras", dataset=self.dataset), [123]))

    def test_update_dataset_extras_reserves_dcat_as_an_exact_key(self):
        # `dcat` is a single key written by the DCAT harvester, not a namespace:
        # neighbouring user keys must stay writable, while the key itself is
        # reserved, as are the `recommendations*` variants the job writes.
        url = url_for("apiv2.dataset_extras", dataset=self.dataset)

        self.assert200(self.put(url, {"dcatIdentifier": "abc"}))
        self.dataset.reload()
        assert self.dataset.extras["dcatIdentifier"] == "abc"

        for key in ("dcat", "recommendations", "recommendations:sources"):
            self.assert400(self.put(url, {key: ["forged"]}))
            self.dataset.reload()
            assert key not in self.dataset.extras

    def test_dataset_url_extra_is_scheme_validated(self):
        # datafairOrigin is registered on the dataset extras too — a distinct
        # registry from the resource one — and feeds an <iframe> src.
        url = url_for("apiv2.dataset_extras", dataset=self.dataset)

        self.assert400(self.put(url, {"datafairOrigin": "javascript:alert(1)"}))

        self.assert200(self.put(url, {"datafairOrigin": "https://datafair.example.org"}))
        self.dataset.reload()
        assert self.dataset.extras["datafairOrigin"] == "https://datafair.example.org"

    def test_admin_can_set_reserved_dataset_extras(self):
        self.login(AdminFactory())
        dataset = DatasetFactory()
        response = self.put(
            url_for("apiv2.dataset_extras", dataset=dataset),
            {"transport:url": "https://transport.data.gouv.fr/x"},
        )
        self.assert200(response)
        dataset.reload()
        assert dataset.extras["transport:url"] == "https://transport.data.gouv.fr/x"

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
    def setUp(self):
        self.login()
        self.dataset = DatasetFactory(owner=self.user)

    def test_get_ressource_extras(self):
        """It should fetch a resource from the API"""
        ResourceMixin.extras.register("check:date", DateTimeField)

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

    def test_update_resource_extras_refreshes_quality(self):
        self.login(AdminFactory())  # Hydra writes platform extras as a sysadmin
        # quality_cached depends on resource extras: check:available feeds the
        # `all_resources_available` indicator, so the targeted update must recompute it.
        resource = ResourceFactory(filetype="remote", extras={"check:available": True})
        self.dataset.resources.append(resource)
        self.dataset.save()
        assert self.dataset.quality["all_resources_available"] is True

        data = {"check:available": False}
        response = self.put(
            url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id), data
        )
        self.assert200(response)

        self.dataset.reload()
        assert self.dataset.resources[0].extras["check:available"] is False
        assert self.dataset.quality["all_resources_available"] is False

    def test_delete_resource_extras_refreshes_quality(self):
        self.login(AdminFactory())  # Hydra writes platform extras as a sysadmin
        # Symmetric to the PUT case: deleting check:available makes the resource
        # availability `unknown` again, so the targeted update must recompute
        # quality_cached on delete too.
        resource = ResourceFactory(filetype="remote", extras={"check:available": False})
        self.dataset.resources.append(resource)
        self.dataset.save()
        assert self.dataset.quality["all_resources_available"] is False

        response = self.delete(
            url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id),
            ["check:available"],
        )
        self.assert204(response)

        self.dataset.reload()
        assert "check:available" not in self.dataset.resources[0].extras
        assert self.dataset.quality["all_resources_available"] is True

    def test_update_resource_extras_refreshes_last_update(self):
        self.login(AdminFactory())  # Hydra writes platform extras as a sysadmin
        # last_update derives from resource.last_modified, which for a remote
        # resource reads the `analysis:last-modified-at` extra. Editing that extra
        # must refresh the dataset's last_update, as Dataset.clean() did on save.
        resource = ResourceFactory(
            filetype="remote", extras={"analysis:last-modified-at": "2024-01-01T00:00:00"}
        )
        self.dataset.resources.append(resource)
        self.dataset.save()
        self.dataset.reload()
        assert self.dataset.last_update == datetime(2024, 1, 1)

        data = {"analysis:last-modified-at": "2024-06-15T12:00:00"}
        response = self.put(
            url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id), data
        )
        self.assert200(response)

        self.dataset.reload()
        assert self.dataset.last_update == datetime(2024, 6, 15, 12, 0, 0)

    def test_update_resource_extras_recomputes_quality_from_the_new_last_update(self):
        self.login(AdminFactory())  # Hydra writes platform extras as a sysadmin
        # quality_cached embeds next_update, which derives from last_update: the
        # targeted update must refresh last_update *before* recomputing quality,
        # otherwise a daily dataset stays late even once its resource is fresh.
        resource = ResourceFactory(
            filetype="remote", extras={"analysis:last-modified-at": "2020-01-01T00:00:00"}
        )
        dataset = DatasetFactory(
            owner=self.user, frequency=UpdateFrequency.DAILY, resources=[resource]
        )
        assert dataset.quality["update_fulfilled_in_time"] is False

        data = {"analysis:last-modified-at": datetime.now(UTC).replace(tzinfo=None).isoformat()}
        response = self.put(
            url_for("apiv2.resource_extras", dataset=dataset, rid=resource.id), data
        )
        self.assert200(response)

        dataset.reload()
        assert dataset.quality["update_fulfilled_in_time"] is True

    def test_delete_resource_extras_refreshes_last_update(self):
        self.login(AdminFactory())  # Hydra writes platform extras as a sysadmin
        # Deleting `analysis:last-modified-at` makes the remote resource fall back
        # to its last_modified_internal, so last_update must no longer be the
        # deleted date.
        resource = ResourceFactory(
            filetype="remote", extras={"analysis:last-modified-at": "2020-01-01T00:00:00"}
        )
        self.dataset.resources.append(resource)
        self.dataset.save()
        self.dataset.reload()
        assert self.dataset.last_update == datetime(2020, 1, 1)

        response = self.delete(
            url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id),
            ["analysis:last-modified-at"],
        )
        self.assert204(response)

        self.dataset.reload()
        assert self.dataset.last_update != datetime(2020, 1, 1)

    def test_update_resource_extras_targets_correct_resource(self):
        self.login(AdminFactory())  # Hydra writes platform extras as a sysadmin
        # The positional $ operator must write to the matched resource only, not to
        # the first resource of the array.
        resources = [ResourceFactory() for _ in range(3)]
        self.dataset.resources.extend(resources)
        self.dataset.save()
        target = resources[1]

        data = {"check:status": 200}
        response = self.put(
            url_for("apiv2.resource_extras", dataset=self.dataset, rid=target.id), data
        )
        self.assert200(response)

        self.dataset.reload()
        assert self.dataset.resources[1].extras["check:status"] == 200
        assert self.dataset.resources[0].extras == {}
        assert self.dataset.resources[2].extras == {}

    def test_delete_resource_extras_targets_correct_resource(self):
        self.login(AdminFactory())  # Hydra writes platform extras as a sysadmin
        # The positional $ operator must delete from the matched resource only.
        resources = [
            ResourceFactory(extras={"check:status": 200, "keep": "value"}) for _ in range(3)
        ]
        self.dataset.resources.extend(resources)
        self.dataset.save()
        target = resources[1]

        response = self.delete(
            url_for("apiv2.resource_extras", dataset=self.dataset, rid=target.id),
            ["check:status"],
        )
        self.assert204(response)

        self.dataset.reload()
        assert "check:status" not in self.dataset.resources[1].extras
        assert self.dataset.resources[1].extras["keep"] == "value"
        assert self.dataset.resources[0].extras["check:status"] == 200
        assert self.dataset.resources[2].extras["check:status"] == 200

    def test_update_resource_extras_rejects_wrongly_typed_extras(self):
        self.login(AdminFactory())  # Hydra writes platform extras as a sysadmin
        # check:available is registered as a BooleanField and check:status as an
        # IntField on the extras field: a targeted update must enforce them just
        # like a full save did, otherwise Hydra can persist a string that
        # check_availability() then reports as available.
        resource = ResourceFactory(extras={"check:available": True})
        self.dataset.resources.append(resource)
        self.dataset.save()
        url = url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id)

        self.assert400(self.put(url, {"check:available": "yes"}))
        self.assert400(self.put(url, {"check:status": "not-an-int"}))

        self.dataset.reload()
        assert self.dataset.resources[0].extras == {"check:available": True}

    def test_update_resource_extras_rejects_reserved_key_for_non_admin(self):
        # analysis:parsing:*_url is produced by the analysis service and rendered
        # by the frontend as a download link; a regular user (even the owner) must
        # not be able to forge it.
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        url = url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id)

        response = self.put(url, {"analysis:parsing:parquet_url": "https://example.org/f.parquet"})
        self.assert400(response)
        assert "analysis:parsing:parquet_url" in response.json["message"]

        self.dataset.reload()
        assert "analysis:parsing:parquet_url" not in self.dataset.resources[0].extras

    def test_update_resource_extras_rejects_reserved_key_deletion_by_null(self):
        # A null value deletes the key: same write vector, same rejection.
        resource = ResourceFactory(extras={"check:available": True})
        self.dataset.resources.append(resource)
        self.dataset.save()
        url = url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id)

        self.assert400(self.put(url, {"check:available": None}))

        self.dataset.reload()
        assert self.dataset.resources[0].extras["check:available"] is True

    def test_delete_resource_extras_rejects_reserved_key_for_non_admin(self):
        resource = ResourceFactory()
        resource.extras = {"check:available": True}
        self.dataset.resources.append(resource)
        self.dataset.save()
        url = url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id)

        self.assert400(self.delete(url, ["check:available"]))

        self.dataset.reload()
        assert self.dataset.resources[0].extras["check:available"] is True

    def test_delete_resource_extras_rejects_non_string_key(self):
        # The payload is a raw JSON list, so its elements are arbitrary values:
        # a non-string must be a 400, not a crash in the reserved-key matching.
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        url = url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id)

        self.assert400(self.delete(url, [123]))

    def test_admin_can_set_reserved_resource_extras(self):
        self.login(AdminFactory())
        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        url = url_for("apiv2.resource_extras", dataset=dataset, rid=resource.id)

        self.assert200(
            self.put(url, {"analysis:parsing:parquet_url": "https://example.org/f.parquet"})
        )
        dataset.reload()
        assert (
            dataset.resources[0].extras["analysis:parsing:parquet_url"]
            == "https://example.org/f.parquet"
        )

    def test_delete_reserved_resource_extra_is_rejected_consistently(self):
        # Rejecting before touching the stored extras makes the outcome independent
        # of a state the caller does not control: a reserved key is a 400 whether it
        # is stored or not, instead of 204 in one case and 404 in the other.
        resource = ResourceFactory(extras={"check:available": True})
        self.dataset.resources.append(resource)
        self.dataset.save()
        url = url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id)

        self.assert400(self.delete(url, ["check:available"]))
        self.assert400(self.delete(url, ["check:status"]))

        self.dataset.reload()
        assert self.dataset.resources[0].extras["check:available"] is True

    def test_reserved_url_extra_rejects_dangerous_scheme(self):
        # Even a sysadmin (Hydra) cannot store a javascript: URL: URLField
        # validation rejects it at the model level, closing the stored-XSS sink.
        self.login(AdminFactory())
        resource = ResourceFactory()
        dataset = DatasetFactory(resources=[resource])
        url = url_for("apiv2.resource_extras", dataset=dataset, rid=resource.id)

        self.assert400(
            self.put(url, {"analysis:parsing:parquet_url": "javascript:alert(document.domain)"})
        )
        dataset.reload()
        assert "analysis:parsing:parquet_url" not in dataset.resources[0].extras

    def test_user_writable_url_extra_is_scheme_validated(self):
        # apidocUrl / datafairOrigin stay user-writable but their scheme is
        # validated, so they cannot carry a javascript:/data: payload.
        resource = ResourceFactory()
        self.dataset.resources.append(resource)
        self.dataset.save()
        url = url_for("apiv2.resource_extras", dataset=self.dataset, rid=resource.id)

        self.assert400(self.put(url, {"apidocUrl": "javascript:alert(1)"}))

        self.assert200(self.put(url, {"apidocUrl": "https://example.org/openapi.json"}))
        self.dataset.reload()
        assert self.dataset.resources[0].extras["apidocUrl"] == "https://example.org/openapi.json"
