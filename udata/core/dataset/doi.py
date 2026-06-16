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


def _doi_request_context(dataset: Dataset) -> tuple[HTTPBasicAuth, str, str]:
    """Validate the dataset and DOI config, returning the auth, platform URI and DOI."""
    if not dataset.organization:
        raise ValueError("Can only reference a dataset created by an organization")
    if not (
        current_app.config["DOI_PREFIX"]
        and current_app.config["DOI_REPO_USER"]
        and current_app.config["DOI_REPO_PWD"]
        and current_app.config["DOI_PLATFORM_URI"]
    ):
        raise ValueError("DOI config is not properly set up")
    auth = HTTPBasicAuth(
        current_app.config["DOI_REPO_USER"],
        current_app.config["DOI_REPO_PWD"],
    )
    doi = f"{current_app.config['DOI_PREFIX']}/{dataset.id}"
    return auth, current_app.config["DOI_PLATFORM_URI"], doi


def _doi_metadata(dataset: Dataset) -> dict:
    """The DOI attributes shared between creation and update."""
    return {
        "titles": [{"title": dataset.title}],
        "publisher": dataset.organization.name,
        "publicationYear": dataset.created_at.strftime("%Y"),
        "url": dataset.url_for(),
    }


def create_doi(dataset: Dataset) -> str:
    auth, platform_uri, doi = _doi_request_context(dataset)
    payload = {
        "data": {
            "type": "dois",
            "attributes": {
                "event": "publish",
                "doi": doi,
                "creators": [{"name": "data.gouv.fr"}],
                "types": {"resourceTypeGeneral": "Dataset"},
                **_doi_metadata(dataset),
            },
        },
    }
    r = requests.post(
        f"{platform_uri}/dois",
        headers=DOI_HEADERS,
        auth=auth,
        json=payload,
        timeout=DOI_REQUEST_TIMEOUT,
    )
    # We post a deterministic DOI (prefix/dataset.id), so DataCite answers 422
    # "This DOI has already been taken" when it already exists: treat it as a success
    # to keep the creation idempotent.
    if r.status_code not in {201, 422}:
        r.raise_for_status()
    return doi


def update_doi(dataset: Dataset) -> str:
    auth, platform_uri, doi = _doi_request_context(dataset)
    payload = {
        "data": {
            "type": "dois",
            "attributes": _doi_metadata(dataset),
        },
    }
    r = requests.put(
        f"{platform_uri}/dois/{doi}",
        headers=DOI_HEADERS,
        auth=auth,
        json=payload,
        timeout=DOI_REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return doi
