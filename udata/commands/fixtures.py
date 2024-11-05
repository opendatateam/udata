"""Commands to download fixtures from the udata-fixtures repository, import them locally.

When "downloading" (generating) the fixtures, save the json as is.
When "importing" the fixtures, massage them so then can be loaded properly.
"""

import json
import logging
import pathlib

import click
import requests
from flask import current_app

from udata.commands import cli
from udata.core.contact_point.factories import ContactPointFactory
from udata.core.contact_point.models import ContactPoint
from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import (
    CommunityResourceFactory,
    DatasetFactory,
    ResourceFactory,
)
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member, Organization
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import UserFactory
from udata.core.user.models import User

log = logging.getLogger(__name__)


DATASET_URL = "/api/1/datasets"
DATASERVICES_URL = "/api/1/dataservices"
ORG_URL = "/api/1/organizations"
REUSE_URL = "/api/1/reuses"
COMMUNITY_RES_URL = "/api/1/datasets/community_resources"
DISCUSSION_URL = "/api/1/discussions"


DEFAULT_FIXTURE_FILE_TAG: str = "v3.0.0"
DEFAULT_FIXTURE_FILE: str = f"https://raw.githubusercontent.com/opendatateam/udata-fixtures/{DEFAULT_FIXTURE_FILE_TAG}/results.json"  # noqa

DEFAULT_FIXTURES_RESULTS_FILENAME: str = "results.json"

UNWANTED_KEYS: dict[str, list[str]] = {
    "dataset": [
        "uri",
        "page",
        "last_update",
        "last_modified",
        "license",
        "badges",
        "spatial",
        "quality",
    ],
    "resource": ["latest", "preview_url", "last_modified"],
    "organization": ["class", "page", "uri", "logo_thumbnail"],
    "reuse": ["datasets", "image_thumbnail", "page", "uri", "owner"],
    "community": [
        "dataset",
        "owner",
        "latest",
        "last_modified",
        "preview_url",
    ],
    "discussion": ["subject", "url", "class"],
    "user": ["uri", "page", "class", "avatar_thumbnail", "email"],
    "posted_by": ["uri", "page", "class", "avatar_thumbnail", "email"],
    "dataservice": [
        "datasets",
        "license",
        "owner",
        "self_api_url",
        "self_web_url",
    ],
}


def remove_unwanted_keys(obj: dict, filter_type: str) -> dict:
    """Remove UNWANTED_KEYS from a dict."""
    if filter_type not in UNWANTED_KEYS:
        return obj
    for unwanted_key in UNWANTED_KEYS[filter_type]:
        if unwanted_key in obj:
            del obj[unwanted_key]
    fix_dates(obj)
    return obj


def fix_dates(obj: dict) -> dict:
    """Fix dates from the fixtures so they can be safely reloaded later on."""
    if "internal" not in obj:
        return obj
    obj["created_at_internal"] = obj["internal"]["created_at_internal"]
    obj["last_modified_internal"] = obj["internal"]["last_modified_internal"]
    del obj["internal"]
    del obj["created_at"]
    return obj


@cli.command()
@click.argument("data-source")
@click.argument("results-filename", default=DEFAULT_FIXTURES_RESULTS_FILENAME)
def generate_fixtures_file(data_source: str, results_filename: str) -> None:
    """Build sample fixture file based on datasets slugs list (users, datasets, reuses, dataservices)."""
    results_file = pathlib.Path(results_filename)
    datasets_slugs = current_app.config["FIXTURE_DATASET_SLUGS"]
    json_result = []

    with click.progressbar(datasets_slugs) as bar:
        for slug in bar:
            json_fixture = {}

            json_dataset = requests.get(f"{data_source}{DATASET_URL}/{slug}/").json()
            json_resources = json_dataset.pop("resources")
            if json_dataset["organization"] is None:
                json_owner = json_dataset.pop("owner")
                json_dataset["owner"] = json_owner["id"]
            else:
                json_org = json_dataset.pop("organization")
                json_org = requests.get(f"{data_source}{ORG_URL}/{json_org['id']}/").json()
                json_fixture["organization"] = json_org
            json_fixture["resources"] = json_resources
            json_fixture["dataset"] = json_dataset

            json_reuses = requests.get(
                f"{data_source}{REUSE_URL}/?dataset={json_dataset['id']}"
            ).json()["data"]
            json_fixture["reuses"] = json_reuses

            json_community = requests.get(
                f"{data_source}{COMMUNITY_RES_URL}/?dataset={json_dataset['id']}"
            ).json()["data"]
            json_fixture["community_resources"] = json_community

            json_discussion = requests.get(
                f"{data_source}{DISCUSSION_URL}/?for={json_dataset['id']}"
            ).json()["data"]
            json_fixture["discussions"] = json_discussion

            json_dataservices = requests.get(
                f"{data_source}{DATASERVICES_URL}/?dataset={json_dataset['id']}"
            ).json()["data"]
            json_fixture["dataservices"] = json_dataservices

            json_result.append(json_fixture)

    with results_file.open("w") as f:
        json.dump(json_result, f, indent=2)
        print(f"Fixtures saved to file {results_filename}")


def get_or_create(data, key, model, factory):
    """Try getting the object. If it doesn't exist yet, create it with the provided factory."""
    if key not in data or data[key] is None:
        return
    data[key] = remove_unwanted_keys(data[key], key)
    obj = model.objects(id=data[key]["id"]).first()
    if not obj:
        obj = factory(**data[key])
    return obj


def get_or_create_organization(data):
    return get_or_create(data, "organization", Organization, OrganizationFactory)


def get_or_create_owner(data):
    return get_or_create(data, "owner", User, UserFactory)


def get_or_create_user(data):
    return get_or_create(data, "user", User, UserFactory)


@cli.command()
@click.argument("source", default=DEFAULT_FIXTURE_FILE)
def import_fixtures(source):
    """Build sample fixture data (users, datasets, reuses, dataservices) from local or remote file."""
    if source.startswith("http"):
        json_fixtures = requests.get(source).json()
    else:
        with open(source) as f:
            json_fixtures = json.load(f)

    with click.progressbar(json_fixtures) as bar:
        for fixture in bar:
            user = UserFactory()
            dataset = fixture["dataset"]
            dataset = remove_unwanted_keys(dataset, "dataset")
            if fixture["organization"]:
                organization = fixture["organization"]
                organization["members"] = [
                    Member(user=get_or_create_user(member), role=member["role"])
                    for member in organization["members"]
                ]
                fixture["organization"] = organization
                org = get_or_create_organization(fixture)
                dataset = DatasetFactory(**dataset, organization=org)
            else:
                dataset = DatasetFactory(**dataset, owner=user)
            for resource in fixture["resources"]:
                resource = remove_unwanted_keys(resource, "resource")
                res = ResourceFactory(**resource)
                dataset.add_resource(res)
            for reuse in fixture["reuses"]:
                reuse = remove_unwanted_keys(reuse, "reuse")
                reuse["owner"] = get_or_create_owner(reuse)
                reuse["organization"] = get_or_create_organization(reuse)
                ReuseFactory(**reuse, datasets=[dataset])
            for community in fixture["community_resources"]:
                community = remove_unwanted_keys(community, "community")
                community["owner"] = get_or_create_owner(community)
                community["organization"] = get_or_create_organization(community)
                CommunityResourceFactory(**community, dataset=dataset)
            for discussion in fixture["discussions"]:
                discussion = remove_unwanted_keys(discussion, "discussion")
                discussion["closed_by"] = get_or_create(discussion, "closed_by", User, UserFactory)
                for message in discussion["discussion"]:
                    message["posted_by"] = get_or_create(message, "posted_by", User, UserFactory)
                discussion["discussion"] = [
                    MessageDiscussionFactory(**message) for message in discussion["discussion"]
                ]
                discussion["user"] = get_or_create_user(discussion)
                DiscussionFactory(**discussion, subject=dataset)
            for dataservice in fixture["dataservices"]:
                dataservice = remove_unwanted_keys(dataservice, "dataservice")
                dataservice["contact_point"] = get_or_create(
                    dataservice, "contact_point", ContactPoint, ContactPointFactory
                )
                dataservice["organization"] = get_or_create_organization(dataservice)
                DataserviceFactory(**dataservice, datasets=[dataset])
