import requests
from flask import current_app
from requests.auth import HTTPBasicAuth

from udata.models import Dataset

# DataCite calls would hang forever without a timeout, like every other HTTP call in udata.
DOI_REQUEST_TIMEOUT = 10

DOI_HEADERS = {
    "accept": "application/vnd.api+json",
    "content-type": "application/json",
}


def _doi_request_context(dataset: Dataset) -> tuple[HTTPBasicAuth, str]:
    """Validate the dataset and DOI config, returning the auth and platform URI."""
    if not dataset.organization:
        raise ValueError("Can only reference a dataset created by an organization")
    if not (
        current_app.config["DOI_PREFIX"]
        and current_app.config["DOI_REPO_USER"]
        and current_app.config["DOI_REPO_PASSWORD"]
        and current_app.config["DOI_PLATFORM_URI"]
    ):
        raise ValueError("DOI config is not properly set up")
    auth = HTTPBasicAuth(
        current_app.config["DOI_REPO_USER"],
        current_app.config["DOI_REPO_PASSWORD"],
    )
    return auth, current_app.config["DOI_PLATFORM_URI"]


def _doi_metadata(dataset: Dataset) -> dict:
    """The DOI attributes shared between creation and update."""
    return {
        "titles": [{"title": dataset.title}],
        "publisher": dataset.organization.name,
        "publicationYear": dataset.created_at.strftime("%Y"),
        # The slug follows the title and can even be taken over by another dataset, so the
        # DOI records the permalink instead.
        "url": dataset.url_for(_useId=True),
    }


def _put_doi(auth: HTTPBasicAuth, platform_uri: str, doi: str, attributes: dict) -> str:
    """Send `attributes` to DataCite.

    PUT upserts, unlike POST which rejects an existing DOI. Since our DOI is deterministic
    (prefix/dataset.id), minting it again is a normal case rather than an error to catch.
    """
    r = requests.put(
        f"{platform_uri}/dois/{doi}",
        headers=DOI_HEADERS,
        auth=auth,
        json={"data": {"type": "dois", "attributes": attributes}},
        timeout=DOI_REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return doi


def create_doi(dataset: Dataset) -> str:
    auth, platform_uri = _doi_request_context(dataset)
    # Publishing is irreversible and the DOI has to resolve, unlike `update_doi` which must
    # keep working once the dataset is archived.
    if dataset.is_hidden:
        raise ValueError("Can only reference a public dataset")
    # The only place a DOI string is built. Everywhere else `dataset.doi` is the truth, so a
    # change of prefix never makes us write to a DOI we did not mint.
    doi = f"{current_app.config['DOI_PREFIX']}/{dataset.id}"
    return _put_doi(
        auth,
        platform_uri,
        doi,
        {
            "event": "publish",
            "doi": doi,
            "creators": [{"name": current_app.config["SITE_TITLE"]}],
            "types": {"resourceTypeGeneral": "Dataset"},
            **_doi_metadata(dataset),
        },
    )


def update_doi(dataset: Dataset) -> str:
    auth, platform_uri = _doi_request_context(dataset)
    if not dataset.doi:
        raise ValueError("Can only update a dataset that has a DOI")
    return _put_doi(auth, platform_uri, dataset.doi, _doi_metadata(dataset))
