import json
import logging

import click
import requests
from flask import current_app

from udata.commands import cli
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

log = logging.getLogger(__name__)


DATASET_URL = "/api/1/datasets"
ORG_URL = "/api/1/organizations"
REUSE_URL = "/api/1/reuses"
COMMUNITY_RES_URL = "/api/1/datasets/community_resources"
DISCUSSION_URL = "/api/1/discussions"


DEFAULT_FIXTURE_FILE = (
    "https://raw.githubusercontent.com/opendatateam/udata-fixtures/main/results.json"  # noqa
)

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
    "organization": ["members", "page", "uri", "logo_thumbnail"],
    "reuse": ["datasets", "image_thumbnail", "page", "uri", "organization", "owner"],
    "community": [
        "dataset",
        "organization",
        "owner",
        "latest",
        "last_modified",
        "preview_url",
    ],
    "discussion": ["subject", "user", "url", "class"],
    "message": ["posted_by"],
}


def remove_unwanted_keys(obj: dict, filter_type: str) -> dict:
    """Remove UNWANTED_KEYS from a dict."""
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


@cli.command()
@click.argument("data-source")
def generate_fixtures_file(data_source):
    """Build sample fixture file based on datasets slugs list (users, datasets, reuses)."""
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

            json_result.append(json_fixture)

    with open("results.json", "w") as f:
        json.dump(json_result, f, indent=2)


@cli.command()
@click.argument("source", default=DEFAULT_FIXTURE_FILE)
def generate_fixtures(source):
    """Build sample fixture data (users, datasets, reuses) from local or remote file."""
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
            if not fixture["organization"]:
                dataset = DatasetFactory(**dataset, owner=user)
            else:
                org = Organization.objects(id=fixture["organization"]["id"]).first()
                if not org:
                    organization = fixture["organization"]
                    organization = remove_unwanted_keys(organization, "organization")
                    org = OrganizationFactory(**organization, members=[Member(user=user)])
                dataset = DatasetFactory(**dataset, organization=org)
            for resource in fixture["resources"]:
                resource = remove_unwanted_keys(resource, "resource")
                res = ResourceFactory(**resource)
                dataset.add_resource(res)
            for reuse in fixture["reuses"]:
                reuse = remove_unwanted_keys(reuse, "reuse")
                ReuseFactory(**reuse, datasets=[dataset], owner=user)
            for community in fixture["community_resources"]:
                community = remove_unwanted_keys(community, "community")
                CommunityResourceFactory(**community, dataset=dataset, owner=user)
            for discussion in fixture["discussions"]:
                discussion = remove_unwanted_keys(discussion, "discussion")
                messages = discussion.pop("discussion")
                for message in messages:
                    message = remove_unwanted_keys(message, "message")
                DiscussionFactory(
                    **discussion,
                    subject=dataset,
                    user=user,
                    discussion=[
                        MessageDiscussionFactory(**message, posted_by=user) for message in messages
                    ],
                )
