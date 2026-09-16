from datetime import UTC, datetime

import pytest
from requests.exceptions import HTTPError

from udata.core.dataset.doi import create_doi, update_doi
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.tests.api import PytestOnlyDBTestCase

PLATFORM_URI = "https://api.test.datacite.org"
PREFIX = "10.1234"


def doi_url(dataset) -> str:
    return f"{PLATFORM_URI}/dois/{PREFIX}/{dataset.id}"


@pytest.mark.options(
    DOI_PREFIX=PREFIX,
    DOI_REPO_USER="user",
    DOI_REPO_PASSWORD="pwd",
    DOI_PLATFORM_URI=PLATFORM_URI,
    CDATA_BASE_URL="https://www.data.gouv.fr",
    SITE_TITLE="data.gouv.fr",
)
class DoiTest(PytestOnlyDBTestCase):
    def test_create_doi(self, rmock):
        dataset = DatasetFactory(
            organization=OrganizationFactory(), created_at_internal=datetime(2020, 3, 1, tzinfo=UTC)
        )
        rmock.put(doi_url(dataset), status_code=201, json={})

        doi = create_doi(dataset)

        assert doi == f"{PREFIX}/{dataset.id}"
        attributes = rmock.last_request.json()["data"]["attributes"]
        assert attributes["event"] == "publish"
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

    def test_create_doi_twice_is_idempotent(self, rmock):
        # Our DOI is deterministic and PUT upserts, so minting it again is a normal case.
        dataset = DatasetFactory(organization=OrganizationFactory())
        rmock.put(
            doi_url(dataset),
            [{"status_code": 201, "json": {}}, {"status_code": 200, "json": {}}],
        )

        assert create_doi(dataset) == f"{PREFIX}/{dataset.id}"
        assert create_doi(dataset) == f"{PREFIX}/{dataset.id}"
        assert rmock.call_count == 2

    def test_create_doi_raises_on_server_error(self, rmock):
        dataset = DatasetFactory(organization=OrganizationFactory())
        rmock.put(doi_url(dataset), status_code=500, json={})

        with pytest.raises(HTTPError):
            create_doi(dataset)

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

    def test_update_doi(self, rmock):
        dataset = DatasetFactory(
            organization=OrganizationFactory(), created_at_internal=datetime(2020, 3, 1, tzinfo=UTC)
        )
        rmock.put(doi_url(dataset), status_code=200, json={})

        doi = update_doi(dataset)

        assert doi == f"{PREFIX}/{dataset.id}"
        attributes = rmock.last_request.json()["data"]["attributes"]
        assert attributes["titles"] == [{"title": dataset.title}]
        assert attributes["publisher"] == dataset.organization.name
        assert attributes["publicationYear"] == "2020"
        assert attributes["url"] == f"https://www.data.gouv.fr/datasets/{dataset.id}"
        # Update only pushes mutable metadata, not the creation-only attributes.
        assert "event" not in attributes
        assert "doi" not in attributes
        assert "creators" not in attributes
        assert "types" not in attributes

    def test_update_doi_raises_on_error(self, rmock):
        dataset = DatasetFactory(organization=OrganizationFactory())
        rmock.put(doi_url(dataset), status_code=404, json={})

        with pytest.raises(HTTPError):
            update_doi(dataset)

    def test_update_doi_without_organization(self, rmock):
        dataset = DatasetFactory()

        with pytest.raises(ValueError):
            update_doi(dataset)

        assert not rmock.called

    def test_update_doi_on_archived_dataset(self, rmock):
        # An archived dataset keeps a public page, so its DOI keeps resolving and its
        # metadata has to stay up to date.
        dataset = DatasetFactory(organization=OrganizationFactory(), archived=datetime.now(UTC))
        rmock.put(doi_url(dataset), status_code=200, json={})

        assert update_doi(dataset) == f"{PREFIX}/{dataset.id}"


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
