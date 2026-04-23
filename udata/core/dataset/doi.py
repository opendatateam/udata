from flask import current_app
import requests
from requests.auth import HTTPBasicAuth

from udata.models import Dataset


def create_doi(dataset: Dataset) -> str:
    if not dataset.organization:
        raise ValueError("Can only reference a dataset created by an organization")
    if not (
        current_app.config["DOI_PREFIX"]
        and current_app.config["DOI_REPO_USER"]
        and current_app.config["DOI_REPO_PWD"]
        and current_app.config["DOI_PLATFORM_URI"]
    ):
        raise ValueError("DOI config is not properly set up")
    basic = HTTPBasicAuth(
        current_app.config["DOI_REPO_USER"],
        current_app.config["DOI_REPO_PWD"],
    )
    doi = f"{current_app.config['DOI_PREFIX']}/{dataset.id}"
    payload = {
        "data": {
            "type": "dois",
            "attributes": {
                "event": "publish",
                "doi": doi,
                "creators": [{"name": "data.gouv.fr"}],
                "titles": [{"title": dataset.title}],
                "publisher": dataset.organization.name,
                "publicationYear": dataset.created_at.strftime("%Y"),
                "types": {"resourceTypeGeneral": "Dataset"},
                "url": dataset.page,
            },
        },
    }
    r = requests.post(
        f"{current_app.config['DOI_PLATFORM_URI']}/dois",
        headers={
            "accept": "application/vnd.api+json",
            "content-type": "application/json",
        },
        auth=basic,
        json=payload,
    )
    if r.status_code not in {201, 422}:  # either created or pre-existing
        r.raise_for_status()
    return doi


def update_doi(dataset: Dataset) -> str:
    if not dataset.organization:
        raise ValueError("Can only reference a dataset created by an organization")
    if not (
        current_app.config["DOI_PREFIX"]
        and current_app.config["DOI_REPO_USER"]
        and current_app.config["DOI_REPO_PWD"]
        and current_app.config["DOI_PLATFORM_URI"]
    ):
        raise ValueError("DOI config is not properly set up")
    basic = HTTPBasicAuth(
        current_app.config["DOI_REPO_USER"],
        current_app.config["DOI_REPO_PWD"],
    )
    payload = {
        "data": {
            "type": "dois",
            "attributes": {
                "titles": [{"title": dataset.title}],
                "publisher": dataset.organization.name,
                "publicationYear": dataset.created_at.strftime("%Y"),  # should we push this?
                "url": dataset.page,
            },
        },
    }
    doi = f"{current_app.config['DOI_PREFIX']}/{dataset.id}"
    r = requests.put(
        f"{current_app.config['DOI_PLATFORM_URI']}/dois/{doi}",
        headers={
            "accept": "application/vnd.api+json",
            "content-type": "application/json",
        },
        auth=basic,
        json=payload,
    )
    r.raise_for_status()
    return doi
