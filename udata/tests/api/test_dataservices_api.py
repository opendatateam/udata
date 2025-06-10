from datetime import datetime
from xml.etree.ElementTree import XML

import feedparser
import pytest
from flask import url_for
from werkzeug.test import TestResponse

import udata.core.organization.constants as org_constants
from udata.core.dataservices.constants import (
    DATASERVICE_ACCESS_TYPE_OPEN,
    DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT,
    DATASERVICE_ACCESS_TYPE_RESTRICTED,
)
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataservices.models import Dataservice
from udata.core.dataset.factories import DatasetFactory, LicenseFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member
from udata.core.user.factories import AdminFactory, UserFactory
from udata.i18n import gettext as _
from udata.tests.helpers import assert200, assert400, assert410, assert_redirects

from . import APITestCase


def dataservice_in_response(response: TestResponse, dataservice: Dataservice) -> bool:
    only_dataservice = [r for r in response.json["data"] if r["id"] == str(dataservice.id)]
    return len(only_dataservice) > 0


class DataserviceAPITest(APITestCase):
    modules = []

    def test_dataservice_api_get(self):
        """It should fetch a dataservice from the API"""
        dataservice = DataserviceFactory()
        response = self.get(url_for("api.dataservice", dataservice=dataservice))
        assert200(response)

    def test_dataservice_api_get_deleted(self):
        """It should not fetch a deleted dataservice from the API and raise 410"""
        dataservice = DataserviceFactory(deleted_at=datetime.utcnow())
        response = self.get(url_for("api.dataservice", dataservice=dataservice))
        assert410(response)

    def test_dataservice_api_get_deleted_but_authorized(self):
        """It should fetch a deleted dataservice from the API if authorized"""
        user = self.login()
        dataservice = DataserviceFactory(deleted_at=datetime.utcnow(), owner=user)
        response = self.get(url_for("api.dataservice", dataservice=dataservice))
        assert200(response)

    def test_dataservice_api_get_private(self):
        """It should not fetch a private dataservice from the API and raise 404"""
        dataservice = DataserviceFactory(private=True)

        response = self.get(url_for("api.dataservice", dataservice=dataservice))
        self.assert404(response)

    def test_dataservice_api_get_private_but_authorized(self):
        """It should fetch a private dataservice from the API if user is authorized"""
        self.login()
        dataservice = DataserviceFactory(owner=self.user, private=True)

        response = self.get(url_for("api.dataservice", dataservice=dataservice))
        self.assert200(response)

    def test_dataservices_api_list_with_filters(self):
        """Should filters dataservices results based on query filters"""
        org = OrganizationFactory()
        org_public_service = OrganizationFactory()
        org_public_service.add_badge(org_constants.PUBLIC_SERVICE)

        _dataservice = DataserviceFactory(organization=org)
        dataservice_public_service = DataserviceFactory(organization=org_public_service)

        response = self.get(
            url_for("api.dataservices", organization_badge=org_constants.PUBLIC_SERVICE)
        )
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(dataservice_public_service.id)

        response = self.get(url_for("api.dataservices", organization_badge="bad-badge"))
        assert400(response)

        # filter on tag
        tag_dataservice = DataserviceFactory(tags=["my-tag", "other"])
        response = self.get(url_for("api.dataservices", tag="my-tag"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == str(tag_dataservice.id)

    def test_dataservice_api_create(self):
        user = self.login()
        datasets = DatasetFactory.create_batch(3)
        license = LicenseFactory.create()

        response = self.post(
            url_for("api.dataservices"),
            {
                "title": "My API",
                "base_api_url": "https://example.org",
            },
        )
        self.assert201(response)
        self.assertEqual(Dataservice.objects.count(), 1)

        dataservice = Dataservice.objects.first()

        response = self.get(url_for("api.dataservice", dataservice=dataservice))
        self.assert200(response)

        self.assertEqual(response.json["title"], "My API")
        self.assertEqual(response.json["base_api_url"], "https://example.org")
        self.assertEqual(response.json["owner"]["id"], str(user.id))

        response = self.patch(
            url_for("api.dataservice", dataservice=dataservice),
            {
                "title": "Updated title",
                "tags": ["hello", "world"],
                "private": True,
                "datasets": [datasets[0].id, datasets[2].id],
                "license": license.id,
                "extras": {
                    "foo": "bar",
                },
            },
        )
        self.assert200(response)

        self.assertEqual(response.json["title"], "Updated title")
        self.assertEqual(response.json["base_api_url"], "https://example.org")
        self.assertEqual(response.json["tags"], ["hello", "world"])
        self.assertEqual(response.json["private"], True)
        self.assertEqual(response.json["extras"], {"foo": "bar"})
        self.assertEqual(response.json["license"], license.id)
        self.assertEqual(
            response.json["self_api_url"], "http://local.test/api/1/dataservices/updated-title/"
        )
        # metadata_modified_at should have been updated during the patch
        self.assertNotEqual(
            response.json["metadata_modified_at"].split("+")[0],
            dataservice.metadata_modified_at.isoformat(),
        )

        self.assertEqual(response.json["datasets"]["total"], 2)
        response_datasets = self.get(response.json["datasets"]["href"])
        self.assert200(response_datasets)
        self.assertEqual(response_datasets.json["total"], 2)
        self.assertEqual(response_datasets.json["data"][0]["title"], datasets[2].title)
        self.assertEqual(response_datasets.json["data"][1]["title"], datasets[0].title)

        dataservice.reload()
        self.assertEqual(dataservice.title, "Updated title")
        self.assertEqual(dataservice.base_api_url, "https://example.org")
        self.assertEqual(dataservice.tags, ["hello", "world"])
        self.assertEqual(dataservice.private, True)
        self.assertEqual(dataservice.datasets[0].title, datasets[0].title)
        self.assertEqual(dataservice.datasets[1].title, datasets[2].title)
        self.assertEqual(
            dataservice.extras,
            {
                "foo": "bar",
            },
        )
        self.assertEqual(dataservice.license.title, license.title)
        self.assertEqual(
            dataservice.self_api_url(), "http://local.test/api/1/dataservices/updated-title/"
        )

        response = self.post(
            url_for("api.dataservice_datasets", dataservice=dataservice),
            [{"id": datasets[0].id}, {"id": datasets[1].id}],
        )
        self.assert201(response)
        self.assertEqual(response.json["datasets"]["total"], 3)
        dataservice.reload()
        self.assertEqual(dataservice.datasets[0].title, datasets[0].title)
        self.assertEqual(dataservice.datasets[1].title, datasets[2].title)
        self.assertEqual(dataservice.datasets[2].title, datasets[1].title)

        response = self.delete(
            url_for("api.dataservice_dataset", dataservice=dataservice, dataset=datasets[0])
        )
        self.assert204(response)
        dataservice.reload()
        self.assertEqual(len(dataservice.datasets), 2)
        self.assertEqual(dataservice.datasets[0].title, datasets[2].title)
        self.assertEqual(dataservice.datasets[1].title, datasets[1].title)

        response = self.delete(
            url_for("api.dataservice_dataset", dataservice=dataservice, dataset=datasets[0])
        )
        self.assert404(response)

        response = self.delete(url_for("api.dataservice", dataservice=dataservice))
        self.assert204(response)

        self.assertEqual(Dataservice.objects.count(), 1)

        dataservice.reload()
        self.assertEqual(dataservice.title, "Updated title")
        self.assertEqual(dataservice.base_api_url, "https://example.org")
        self.assertIsNotNone(dataservice.deleted_at)

        # We can access deleted element as the creator
        response = self.get(url_for("api.dataservice", dataservice=dataservice))
        self.assert200(response)

        # We cannot access private element as random user
        self.login()
        response = self.get(url_for("api.dataservice", dataservice=dataservice))
        self.assert404(response)

        # We can undelete with a patch
        self.login(user)
        response = self.patch(
            url_for("api.dataservice", dataservice=dataservice),
            {
                "title": "Undeleted title",
                "deleted_at": None,
            },
        )
        self.assert200(response)

        dataservice.reload()
        self.assertEqual(dataservice.title, "Undeleted title")
        self.assertIsNone(dataservice.deleted_at)

    def test_dataservice_api_list_owned(self) -> None:
        """Should filter out private dataservices if not owner"""
        owner = UserFactory()
        org = OrganizationFactory()
        public_dataservice = DataserviceFactory()
        private_user_dataservice = DataserviceFactory(private=True, owner=owner)
        private_org_dataservice = DataserviceFactory(private=True, organization=org)

        # Only public dataservices for non-authenticated user.
        response = self.get(url_for("api.dataservices"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert dataservice_in_response(response, public_dataservice)

        # Only public dataservices for a non-owner authenticated user.
        self.login(UserFactory())
        response = self.get(url_for("api.dataservices"))
        assert200(response)
        assert len(response.json["data"]) == 1
        assert dataservice_in_response(response, public_dataservice)

        # Authenticated user is the owner
        self.login(owner)

        # Public and 1 private dataservice for the owner
        response = self.get(url_for("api.dataservices"))
        assert200(response)
        assert len(response.json["data"]) == 2  # Return everything
        assert dataservice_in_response(response, public_dataservice)
        assert dataservice_in_response(response, private_user_dataservice)

        # Authenticated user is now also member of the organization
        member = Member(user=owner, role="editor")
        org.members = [member]
        org.save()
        del owner.organizations  # clear user.organizations cached property
        owner.reload()

        # Public and 2 private dataservices for the owner + organization member
        response = self.get(url_for("api.dataservices"))
        assert200(response)
        assert len(response.json["data"]) == 3  # Return everything
        assert dataservice_in_response(response, public_dataservice)
        assert dataservice_in_response(response, private_user_dataservice)
        assert dataservice_in_response(response, private_org_dataservice)

    def test_dataservice_api_index(self):
        dataset_a = DatasetFactory(title="Dataset A")
        dataset_b = DatasetFactory(title="Dataset B")

        self.login()
        self.post(
            url_for("api.dataservices"),
            {
                "title": "B",
                "base_api_url": "https://example.org/B",
                "datasets": [dataset_b.id],
                "access_type": DATASERVICE_ACCESS_TYPE_OPEN,
            },
        )
        self.post(
            url_for("api.dataservices"),
            {
                "title": "C",
                "base_api_url": "https://example.org/C",
                "datasets": [dataset_a.id, dataset_b.id],
                "access_type": DATASERVICE_ACCESS_TYPE_OPEN_WITH_ACCOUNT,
            },
        )
        self.post(
            url_for("api.dataservices"),
            {
                "title": "A",
                "base_api_url": "https://example.org/A",
                "datasets": [dataset_a.id],
                "access_type": DATASERVICE_ACCESS_TYPE_RESTRICTED,
            },
        )
        self.post(
            url_for("api.dataservices"),
            {
                "title": "X",
                "base_api_url": "https://example.org/X",
                "private": True,
                "datasets": [dataset_a.id],
            },
        )

        self.assertEqual(Dataservice.objects.count(), 4)

        # Login with a distinct user, without visibility on the private dataservice
        self.login(UserFactory())

        response = self.get(url_for("api.dataservices"))
        self.assert200(response)

        self.assertEqual(response.json["previous_page"], None)
        self.assertEqual(response.json["next_page"], None)
        self.assertEqual(response.json["page"], 1)
        self.assertEqual(response.json["total"], 3)
        self.assertEqual(len(response.json["data"]), 3)
        self.assertEqual(response.json["data"][0]["title"], "B")
        self.assertEqual(response.json["data"][1]["title"], "C")
        self.assertEqual(response.json["data"][2]["title"], "A")

        response_datasets = self.get(response.json["data"][0]["datasets"]["href"])
        self.assert200(response_datasets)
        self.assertEqual(response_datasets.json["total"], 1)
        self.assertEqual(response_datasets.json["data"][0]["id"], str(dataset_b.id))

        response_datasets = self.get(response.json["data"][1]["datasets"]["href"])
        self.assert200(response_datasets)
        self.assertEqual(response_datasets.json["total"], 2)
        self.assertEqual(response_datasets.json["data"][0]["id"], str(dataset_b.id))
        self.assertEqual(response_datasets.json["data"][1]["id"], str(dataset_a.id))

        response_datasets = self.get(response.json["data"][2]["datasets"]["href"])
        self.assert200(response_datasets)
        self.assertEqual(response_datasets.json["total"], 1)
        self.assertEqual(response_datasets.json["data"][0]["id"], str(dataset_a.id))

        response = self.get(url_for("api.dataservices", page_size=1))
        self.assert200(response)

        self.assertEqual(response.json["previous_page"], None)
        assert response.json["next_page"].endswith(url_for("api.dataservices", page_size=1, page=2))
        self.assertEqual(response.json["page"], 1)
        self.assertEqual(response.json["total"], 3)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertEqual(response.json["data"][0]["title"], "B")

        response = self.get(url_for("api.dataservices", sort="title", dataset=str(dataset_a.id)))
        self.assert200(response)

        self.assertEqual(response.json["total"], 2)
        self.assertEqual(response.json["data"][0]["title"], "A")
        self.assertEqual(response.json["data"][1]["title"], "C")

        response = self.get(url_for("api.dataservices", access_type=DATASERVICE_ACCESS_TYPE_OPEN))
        self.assert200(response)

        print(response.json)
        self.assertEqual(response.json["total"], 1)
        self.assertEqual(response.json["data"][0]["title"], "B")

    def test_dataservice_api_index_with_sorts(self):
        DataserviceFactory(title="A", created_at="2024-03-01", metadata_modified_at="2024-03-01")
        DataserviceFactory(
            title="B",
            created_at="2024-02-01",
            metadata_modified_at="2024-05-01",
            metrics={"views": 42},
        )
        DataserviceFactory(
            title="C",
            created_at="2024-05-01",
            metadata_modified_at="2024-04-01",
            metrics={"views": 1337},
        )
        DataserviceFactory(title="D", created_at="2024-04-01", metadata_modified_at="2024-02-01")

        response = self.get(url_for("api.dataservices", sort="title"))
        self.assert200(response)
        self.assertEqual(
            [dataservice["title"] for dataservice in response.json["data"]], ["A", "B", "C", "D"]
        )

        response = self.get(url_for("api.dataservices", sort="-title"))
        self.assert200(response)
        self.assertEqual(
            [dataservice["title"] for dataservice in response.json["data"]], ["D", "C", "B", "A"]
        )

        response = self.get(url_for("api.dataservices", sort="created"))
        self.assert200(response)
        self.assertEqual(
            [dataservice["title"] for dataservice in response.json["data"]], ["B", "A", "D", "C"]
        )

        response = self.get(url_for("api.dataservices", sort="-created"))
        self.assert200(response)
        self.assertEqual(
            [dataservice["title"] for dataservice in response.json["data"]], ["C", "D", "A", "B"]
        )

        response = self.get(url_for("api.dataservices", sort="last_modified"))
        self.assert200(response)
        self.assertEqual(
            [dataservice["title"] for dataservice in response.json["data"]], ["D", "A", "C", "B"]
        )

        response = self.get(url_for("api.dataservices", sort="-last_modified"))
        self.assert200(response)
        self.assertEqual(
            [dataservice["title"] for dataservice in response.json["data"]], ["B", "C", "A", "D"]
        )

        response = self.get(url_for("api.dataservices", sort="views"))
        self.assert200(response)

        self.assertEqual(
            [dataservice["title"] for dataservice in response.json["data"]], ["A", "D", "B", "C"]
        )

        response = self.get(url_for("api.dataservices", sort="-views"))
        self.assert200(response)

        self.assertEqual(
            [dataservice["title"] for dataservice in response.json["data"]], ["C", "B", "D", "A"]
        )

    def test_dataservice_api_index_with_wrong_dataset_id(self):
        response = self.get(url_for("api.dataservices", sort="title", dataset=str("xxx")))
        self.assert400(response)

    def test_dataservice_api_create_with_validation_error(self):
        self.login()
        response = self.post(
            url_for("api.dataservices"),
            {
                "base_api_url": "https://example.org",
            },
        )
        self.assert400(response)
        self.assertEqual(Dataservice.objects.count(), 0)

    def test_dataservice_api_create_with_unkwown_license(self):
        self.login()
        response = self.post(
            url_for("api.dataservices"),
            {
                "title": "My title",
                "base_api_url": "https://example.org",
                "license": "unwkown-license",
            },
        )
        self.assert400(response)
        self.assertEqual(response.json["errors"]["license"], "Unknown reference 'unwkown-license'")
        self.assertEqual(Dataservice.objects.count(), 0)

    def test_dataservice_api_create_with_unkwown_contact_point(self):
        self.login()

        response = self.post(
            url_for("api.dataservices"),
            {
                "title": "My title",
                "base_api_url": "https://example.org",
                "contact_points": ["66212433e42ab56639ad516e"],
            },
        )
        self.assert400(response)
        self.assertEqual(
            response.json["errors"]["contact_points"],
            "Unknown reference '66212433e42ab56639ad516e'",
        )
        self.assertEqual(Dataservice.objects.count(), 0)

    def test_dataservice_api_create_with_custom_user_or_org(self):
        other = UserFactory()
        other_member = Member(user=other, role="editor")
        other_org = OrganizationFactory(members=[other_member])

        me = self.login()
        me_member = Member(user=me, role="editor")
        me_org = OrganizationFactory(members=[me_member])

        response = self.post(
            url_for("api.dataservices"),
            {
                "title": "My title",
                "base_api_url": "https://example.org",
                "owner": other.id,
            },
        )
        self.assert400(response)
        print(response.json)
        self.assertEqual(response.json["errors"]["owner"], _("You can only set yourself as owner"))
        self.assertEqual(Dataservice.objects.count(), 0)

        response = self.post(
            url_for("api.dataservices"),
            {
                "title": "My title",
                "base_api_url": "https://example.org",
                "organization": other_org.id,
            },
        )
        self.assert400(response)
        self.assertEqual(
            response.json["errors"]["organization"], _("Permission denied for this organization")
        )
        self.assertEqual(Dataservice.objects.count(), 0)

        response = self.post(
            url_for("api.dataservices"),
            {
                "title": "My title",
                "base_api_url": "https://example.org",
                "owner": me.id,
            },
        )
        self.assert201(response)
        dataservice = Dataservice.objects(id=response.json["id"]).first()
        self.assertEqual(dataservice.owner.id, me.id)
        self.assertEqual(dataservice.organization, None)

        response = self.post(
            url_for("api.dataservices"),
            {
                "title": "My title",
                "base_api_url": "https://example.org",
                "organization": me_org.id,
            },
        )
        self.assert201(response)
        dataservice = Dataservice.objects(id=response.json["id"]).first()
        self.assertEqual(dataservice.owner, None)
        self.assertEqual(dataservice.organization.id, me_org.id)

    def test_dataservice_api_update_org(self):
        """It shouldn't update the dataservice org"""
        user = self.login()
        original_member = Member(user=user, role="editor")
        original_org = OrganizationFactory(members=[original_member])
        dataservice = DataserviceFactory(owner=user, organization=original_org)

        new_member = Member(user=self.user, role="admin")
        new_org = OrganizationFactory(members=[new_member])

        data = dataservice.to_dict()
        data["organization"] = {"id": new_org.id}
        response = self.patch(url_for("api.dataservice", dataservice=dataservice), data)
        self.assert400(response)
        self.assertEqual(Dataservice.objects.count(), 1)
        self.assertNotEqual(Dataservice.objects.first().organization.id, new_org.id)

        self.login(AdminFactory())
        data = dataservice.to_dict()
        data["organization"] = {"id": new_org.id}
        response = self.patch(url_for("api.dataservice", dataservice=dataservice), data)
        self.assert200(response)
        self.assertEqual(Dataservice.objects.count(), 1)
        self.assertEqual(Dataservice.objects.first().organization.id, new_org.id)


@pytest.mark.frontend
class DataserviceRdfViewsTest:
    def test_rdf_default_to_jsonld(self, client):
        dataservice = DataserviceFactory()
        expected = url_for("api.dataservice_rdf_format", dataservice=dataservice.id, format="json")
        response = client.get(url_for("api.dataservice_rdf", dataservice=dataservice))
        assert_redirects(response, expected)

    def test_rdf_perform_content_negociation(self, client):
        dataservice = DataserviceFactory()
        expected = url_for("api.dataservice_rdf_format", dataservice=dataservice.id, format="xml")
        url = url_for("api.dataservice_rdf", dataservice=dataservice)
        headers = {"accept": "application/xml"}
        response = client.get(url, headers=headers)
        assert_redirects(response, expected)

    def test_rdf_perform_content_negociation_response(self, client):
        """Check we have valid XML as output"""
        dataservice = DataserviceFactory()
        url = url_for("api.dataservice_rdf", dataservice=dataservice)
        headers = {"accept": "application/xml"}
        response = client.get(url, headers=headers, follow_redirects=True)
        element = XML(response.data)
        assert element.tag == "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"

    def test_dataservice_rdf_json_ld(self, client):
        dataservice = DataserviceFactory()
        for fmt in "json", "jsonld":
            url = url_for("api.dataservice_rdf_format", dataservice=dataservice, format=fmt)
            response = client.get(url, headers={"Accept": "application/ld+json"})
            assert200(response)
            assert response.content_type == "application/ld+json"
            assert response.json["@context"]["@vocab"] == "http://www.w3.org/ns/dcat#"

    @pytest.mark.parametrize(
        "fmt,mime",
        [
            ("n3", "text/n3"),
            ("nt", "application/n-triples"),
            ("ttl", "application/x-turtle"),
            ("xml", "application/rdf+xml"),
            ("rdf", "application/rdf+xml"),
            ("owl", "application/rdf+xml"),
            ("trig", "application/trig"),
        ],
    )
    def test_dataservice_rdf_formats(self, client, fmt, mime):
        dataservice = DataserviceFactory()
        url = url_for("api.dataservice_rdf_format", dataservice=dataservice, format=fmt)
        response = client.get(url, headers={"Accept": mime})
        assert200(response)
        assert response.content_type == mime


class DataservicesFeedAPItest(APITestCase):
    def test_recent_feed(self):
        dataservices = [DataserviceFactory() for i in range(3)]

        response = self.get(url_for("api.recent_dataservices_atom_feed"))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), len(dataservices))
        for i in range(1, len(feed.entries)):
            published_date = feed.entries[i].published_parsed
            prev_published_date = feed.entries[i - 1].published_parsed
            self.assertGreaterEqual(prev_published_date, published_date)

    def test_recent_feed_owner(self):
        owner = UserFactory()
        DataserviceFactory(owner=owner)

        response = self.get(url_for("api.recent_dataservices_atom_feed"))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, owner.fullname)
        self.assertEqual(author.href, owner.external_url)

    def test_recent_feed_org(self):
        owner = UserFactory()
        org = OrganizationFactory()
        DataserviceFactory(owner=owner, organization=org)

        response = self.get(url_for("api.recent_dataservices_atom_feed"))

        self.assert200(response)

        feed = feedparser.parse(response.data)

        self.assertEqual(len(feed.entries), 1)
        entry = feed.entries[0]
        self.assertEqual(len(entry.authors), 1)
        author = entry.authors[0]
        self.assertEqual(author.name, org.name)
        self.assertEqual(author.href, org.external_url)
