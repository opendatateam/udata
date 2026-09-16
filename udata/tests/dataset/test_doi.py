from datetime import UTC, datetime

import pytest
from flask import url_for
from requests.exceptions import HTTPError

from udata.core.dataset.doi import create_doi, update_doi
from udata.core.dataset.factories import DatasetFactory
from udata.core.dataset.models import Dataset
from udata.core.dataset.tasks import purge_datasets
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.tests.api import PytestOnlyAPITestCase, PytestOnlyDBTestCase

PLATFORM_URI = "https://api.test.datacite.org"
PREFIX = "10.1234"

DOI_OPTIONS = {
    "DOI_PREFIX": PREFIX,
    "DOI_REPO_USER": "user",
    "DOI_REPO_PASSWORD": "pwd",
    "DOI_PLATFORM_URI": PLATFORM_URI,
    "CDATA_BASE_URL": "https://www.data.gouv.fr",
    "SITE_TITLE": "data.gouv.fr",
}


def doi_url(dataset) -> str:
    return f"{PLATFORM_URI}/dois/{PREFIX}/{dataset.id}"


@pytest.mark.options(**DOI_OPTIONS)
class DoiTest(PytestOnlyDBTestCase):
    def test_create_doi(self, datacite, rmock):
        dataset = DatasetFactory(
            organization=OrganizationFactory(), created_at_internal=datetime(2020, 3, 1, tzinfo=UTC)
        )

        doi = create_doi(dataset)

        assert doi == f"{PREFIX}/{dataset.id}"
        attributes = datacite.attributes_of(doi)
        assert attributes["state"] == "findable"
        assert attributes["doi"] == doi
        assert attributes["creators"] == [{"name": "data.gouv.fr"}]
        assert attributes["types"] == {"resourceTypeGeneral": "Dataset"}
        assert attributes["titles"] == [{"title": dataset.title}]
        assert attributes["publisher"] == dataset.organization.name
        assert attributes["publicationYear"] == "2020"
        # The permalink, not the slug: a DOI has to keep resolving after a rename.
        assert attributes["url"] == f"https://www.data.gouv.fr/datasets/{dataset.id}"
        # The configured credentials are sent as HTTP basic auth: base64("user:pwd").
        assert rmock.last_request.headers["Authorization"] == "Basic dXNlcjpwd2Q="

    def test_create_doi_twice_is_idempotent(self, datacite):
        # Our DOI is deterministic and PUT upserts, so minting it again is a normal case.
        dataset = DatasetFactory(organization=OrganizationFactory())

        assert create_doi(dataset) == f"{PREFIX}/{dataset.id}"
        assert create_doi(dataset) == f"{PREFIX}/{dataset.id}"

        assert list(datacite.dois) == [f"{PREFIX}/{dataset.id}"]

    def test_create_doi_raises_on_server_error(self, datacite):
        dataset = DatasetFactory(organization=OrganizationFactory())
        datacite.fails_with(500)

        with pytest.raises(HTTPError):
            create_doi(dataset)

        assert not datacite.dois

    def test_create_doi_without_organization(self, rmock):
        dataset = DatasetFactory()

        with pytest.raises(ValueError):
            create_doi(dataset)

        assert not rmock.called

    @pytest.mark.parametrize(
        "hidden",
        [{"private": True}, {"deleted": datetime.now(UTC)}, {"archived": datetime.now(UTC)}],
    )
    def test_create_doi_on_hidden_dataset(self, rmock, hidden):
        dataset = DatasetFactory(organization=OrganizationFactory(), **hidden)

        with pytest.raises(ValueError):
            create_doi(dataset)

        assert not rmock.called

    def test_update_doi(self, datacite):
        dataset = DatasetFactory(
            organization=OrganizationFactory(), created_at_internal=datetime(2020, 3, 1, tzinfo=UTC)
        )
        dataset.doi = create_doi(dataset)

        dataset.title = "A brand new title"
        doi = update_doi(dataset)

        assert doi == f"{PREFIX}/{dataset.id}"
        # The update lands on the DOI that was minted, and only pushes mutable metadata.
        assert list(datacite.dois) == [doi]
        assert datacite.attributes_of(doi)["titles"] == [{"title": "A brand new title"}]
        assert datacite.attributes_of(doi)["state"] == "findable"
        pushed = datacite.requests[-1]["attributes"]
        assert set(pushed) == {"titles", "publisher", "publicationYear", "url"}

    def test_update_doi_raises_on_error(self, datacite):
        dataset = DatasetFactory(organization=OrganizationFactory(), doi=f"{PREFIX}/minted")
        datacite.fails_with(404)

        with pytest.raises(HTTPError):
            update_doi(dataset)

    def test_update_doi_without_a_doi(self, datacite):
        dataset = DatasetFactory(organization=OrganizationFactory())

        with pytest.raises(ValueError):
            update_doi(dataset)

        assert not datacite.dois

    def test_update_doi_targets_the_stored_doi_after_a_prefix_change(self, app, datacite):
        # Moving to another DataCite repository must not mint a second DOI for the dataset.
        dataset = DatasetFactory(organization=OrganizationFactory())
        dataset.doi = create_doi(dataset)
        app.config["DOI_PREFIX"] = "10.9999"

        update_doi(dataset)

        assert list(datacite.dois) == [dataset.doi]

    def test_update_doi_without_organization(self, rmock):
        dataset = DatasetFactory()

        with pytest.raises(ValueError):
            update_doi(dataset)

        assert not rmock.called

    def test_update_doi_on_archived_dataset(self, datacite):
        # An archived dataset keeps a public page, so its DOI keeps resolving and its
        # metadata has to stay up to date.
        dataset = DatasetFactory(organization=OrganizationFactory())
        dataset.doi = create_doi(dataset)

        dataset.archived = datetime.now(UTC)
        doi = update_doi(dataset)

        assert datacite.attributes_of(doi)["state"] == "findable"


@pytest.mark.options(
    # Pinned rather than left to the defaults: a local `udata.cfg` is loaded on top of them
    # and would give these tests a working configuration.
    DOI_PREFIX=None,
    DOI_REPO_USER=None,
    DOI_REPO_PASSWORD=None,
    DOI_PLATFORM_URI=None,
)
class DoiWithoutConfigTest(PytestOnlyDBTestCase):
    def test_create_doi_without_config(self, rmock):
        dataset = DatasetFactory(organization=OrganizationFactory())

        with pytest.raises(ValueError):
            create_doi(dataset)

        assert not rmock.called

    def test_update_doi_without_config(self, rmock):
        dataset = DatasetFactory(organization=OrganizationFactory())

        with pytest.raises(ValueError):
            update_doi(dataset)

        assert not rmock.called


@pytest.mark.options(**DOI_OPTIONS)
class DoiAPITest(PytestOnlyAPITestCase):
    def test_mint_doi(self, datacite):
        self.login(AdminFactory())
        dataset = DatasetFactory(organization=OrganizationFactory())

        response = self.post(url_for("api.dataset_doi", dataset=dataset))

        self.assert200(response)
        dataset.reload()
        assert dataset.doi == f"{PREFIX}/{dataset.id}"
        assert response.json["doi"] == dataset.doi
        assert datacite.attributes_of(dataset.doi)["state"] == "findable"

    def test_mint_doi_requires_an_admin(self, datacite):
        self.login(UserFactory())
        dataset = DatasetFactory(organization=OrganizationFactory())

        response = self.post(url_for("api.dataset_doi", dataset=dataset))

        self.assert403(response)
        dataset.reload()
        assert dataset.doi is None
        assert not datacite.dois

    def test_mint_doi_twice_is_refused(self, datacite):
        self.login(AdminFactory())
        dataset = DatasetFactory(organization=OrganizationFactory(), doi=f"{PREFIX}/already")

        response = self.post(url_for("api.dataset_doi", dataset=dataset))

        self.assertStatus(response, 409)
        dataset.reload()
        assert dataset.doi == f"{PREFIX}/already"
        assert not datacite.dois

    def test_mint_doi_on_hidden_dataset_is_refused(self, datacite):
        self.login(AdminFactory())
        dataset = DatasetFactory(organization=OrganizationFactory(), private=True)

        response = self.post(url_for("api.dataset_doi", dataset=dataset))

        self.assert400(response)
        dataset.reload()
        assert dataset.doi is None
        assert not datacite.dois

    def test_dataset_with_a_doi_cannot_be_deleted(self):
        user = self.login()
        dataset = DatasetFactory(owner=user, doi=f"{PREFIX}/minted")

        response = self.delete(url_for("api.dataset", dataset=dataset))

        self.assertStatus(response, 409)
        dataset.reload()
        assert dataset.deleted is None


@pytest.mark.options(**DOI_OPTIONS)
class DoiSyncTest(PytestOnlyDBTestCase):
    def test_title_change_pushes_metadata(self, datacite):
        dataset = DatasetFactory(organization=OrganizationFactory())
        dataset.doi = create_doi(dataset)
        dataset.save()

        dataset.title = "A brand new title"
        dataset.save()

        # The DOI that was minted is updated, not a second one created next to it.
        assert list(datacite.dois) == [dataset.doi]
        assert datacite.attributes_of(dataset.doi)["titles"] == [{"title": "A brand new title"}]

    def test_unrelated_change_does_not_push_metadata(self, datacite):
        dataset = DatasetFactory(organization=OrganizationFactory())
        dataset.doi = create_doi(dataset)
        dataset.save()
        pushes = len(datacite.requests)

        dataset.description = "A brand new description"
        dataset.save()

        assert len(datacite.requests) == pushes

    def test_dataset_without_doi_never_pushes_metadata(self, datacite):
        dataset = DatasetFactory(organization=OrganizationFactory())

        dataset.title = "A brand new title"
        dataset.save()

        assert not datacite.dois

    def test_purge_keeps_datasets_with_a_doi(self, datacite):
        kept = DatasetFactory(
            organization=OrganizationFactory(), doi=f"{PREFIX}/minted", deleted=datetime.now(UTC)
        )
        purged = DatasetFactory(organization=OrganizationFactory(), deleted=datetime.now(UTC))

        purge_datasets()

        kept.reload()
        assert Dataset.objects(id=purged.id).first() is None
