import pytest
from requests.exceptions import HTTPError

from udata.core.dataset.doi import create_doi, update_doi
from udata.core.dataset.factories import DatasetFactory
from udata.core.organization.factories import OrganizationFactory
from udata.tests.api import PytestOnlyDBTestCase

PLATFORM_URI = "https://api.test.datacite.org"
PREFIX = "10.1234"
POST_URL = f"{PLATFORM_URI}/dois"


@pytest.mark.options(
    DOI_PREFIX=PREFIX,
    DOI_REPO_USER="user",
    DOI_REPO_PWD="pwd",
    DOI_PLATFORM_URI=PLATFORM_URI,
    CDATA_BASE_URL="https://www.data.gouv.fr",
)
class DoiTest(PytestOnlyDBTestCase):
    def test_create_doi(self, rmock):
        dataset = DatasetFactory(organization=OrganizationFactory())
        rmock.post(POST_URL, status_code=201, json={})

        doi = create_doi(dataset)

        assert doi == f"{PREFIX}/{dataset.id}"
        attributes = rmock.last_request.json()["data"]["attributes"]
        assert attributes["event"] == "publish"
        assert attributes["doi"] == doi
        assert attributes["creators"] == [{"name": "data.gouv.fr"}]
        assert attributes["types"] == {"resourceTypeGeneral": "Dataset"}
        assert attributes["titles"] == [{"title": dataset.title}]
        assert attributes["publisher"] == dataset.organization.name
        assert attributes["publicationYear"] == dataset.created_at.strftime("%Y")
        assert attributes["url"] == dataset.url_for()
        # Credentials are sent as HTTP basic auth.
        assert rmock.last_request.headers["Authorization"].startswith("Basic ")

    def test_create_doi_already_exists_is_idempotent(self, rmock):
        # DataCite answers 422 "This DOI has already been taken" for our deterministic DOI:
        # creation must succeed instead of raising.
        dataset = DatasetFactory(organization=OrganizationFactory())
        rmock.post(POST_URL, status_code=422, json={})

        doi = create_doi(dataset)

        assert doi == f"{PREFIX}/{dataset.id}"

    def test_create_doi_raises_on_server_error(self, rmock):
        dataset = DatasetFactory(organization=OrganizationFactory())
        rmock.post(POST_URL, status_code=500, json={})

        with pytest.raises(HTTPError):
            create_doi(dataset)

    def test_create_doi_without_organization(self, rmock):
        dataset = DatasetFactory()

        with pytest.raises(ValueError):
            create_doi(dataset)

        assert not rmock.called

    def test_update_doi(self, rmock):
        dataset = DatasetFactory(organization=OrganizationFactory())
        put_url = f"{PLATFORM_URI}/dois/{PREFIX}/{dataset.id}"
        rmock.put(put_url, status_code=200, json={})

        doi = update_doi(dataset)

        assert doi == f"{PREFIX}/{dataset.id}"
        attributes = rmock.last_request.json()["data"]["attributes"]
        assert attributes["titles"] == [{"title": dataset.title}]
        assert attributes["publisher"] == dataset.organization.name
        assert attributes["publicationYear"] == dataset.created_at.strftime("%Y")
        assert attributes["url"] == dataset.url_for()
        # Update only pushes mutable metadata, not the creation-only attributes.
        assert "event" not in attributes
        assert "doi" not in attributes
        assert "creators" not in attributes
        assert "types" not in attributes

    def test_update_doi_raises_on_error(self, rmock):
        dataset = DatasetFactory(organization=OrganizationFactory())
        put_url = f"{PLATFORM_URI}/dois/{PREFIX}/{dataset.id}"
        rmock.put(put_url, status_code=404, json={})

        with pytest.raises(HTTPError):
            update_doi(dataset)

    def test_update_doi_without_organization(self, rmock):
        dataset = DatasetFactory()

        with pytest.raises(ValueError):
            update_doi(dataset)

        assert not rmock.called


class DoiWithoutConfigTest(PytestOnlyDBTestCase):
    # No DOI_* options here: the config defaults to None, so both calls must refuse
    # to reach DataCite.
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
