import requests
from flask import current_app
from requests.auth import HTTPBasicAuth

from udata.models import Dataset, Organization
from udata.tasks import task

# DataCite calls would hang forever without a timeout.
DOI_REQUEST_TIMEOUT = 10

DOI_HEADERS = {"accept": "application/vnd.api+json"}


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


#: The dataset fields `_doi_metadata` reads and that a user can change. Lives here so that
#: adding an attribute below is not silently forgotten by the watcher that pushes updates.
#: `url` is a permalink and `publicationYear` derives from non-auditable fields.
DOI_METADATA_FIELDS = {"title", "organization"}


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


@task(route="high.dataset")
def push_doi_metadata(dataset_id: str) -> None:
    dataset = Dataset.objects(id=dataset_id).first()
    # An organization can be dropped after the DOI was minted (transfer to a user, organization
    # deletion). DataCite then keeps the publisher it was given, which is the one that was true
    # when the DOI was minted.
    if dataset and dataset.doi and dataset.organization:
        update_doi(dataset)


@Dataset.on_update.connect
def update_doi_on_metadata_change(dataset, **kwargs) -> None:
    """Keep DataCite in sync with the metadata it records for an already minted DOI."""
    if dataset.doi and DOI_METADATA_FIELDS.intersection(kwargs.get("changed_fields", [])):
        push_doi_metadata.delay(str(dataset.id))


@Organization.on_update.connect
def update_doi_on_organization_rename(organization, **kwargs) -> None:
    """Renaming an organization changes the DataCite publisher of every DOI it produced.

    Saving an organization emits no `Dataset.on_update`, so the dataset watcher above cannot
    see this one.
    """
    if "name" not in kwargs.get("changed_fields", []):
        return
    for dataset in Dataset.objects(organization=organization, doi__ne=None).only("id"):
        push_doi_metadata.delay(str(dataset.id))
