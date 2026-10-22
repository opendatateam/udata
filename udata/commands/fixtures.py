"""Commands to generate and import fixtures locally.

When "downloading" (generating) the fixtures, save the json as is.
When "importing" the fixtures, massage them so they can be loaded properly.
"""

import json
import logging
import pathlib
from collections.abc import Callable

import click
import requests
from flask import current_app
from mongoengine.fields import ReferenceField

from udata.api_fields import classes_by_parents, patch
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
from udata.core.edito_blocs.base import Bloc
from udata.core.edito_blocs.models import SITE_BLOCS_FIELDS
from udata.core.organization.factories import OrganizationFactory
from udata.core.organization.models import Member, Organization
from udata.core.owned import ownership_filter
from udata.core.post.factories import PostFactory
from udata.core.post.models import Post
from udata.core.reuse.factories import ReuseFactory
from udata.core.site.factories import SiteFactory
from udata.core.site.models import Site
from udata.core.user.factories import UserFactory
from udata.core.user.models import User

log = logging.getLogger(__name__)


DATASET_URL = "/api/1/datasets"
DATASERVICES_URL = "/api/1/dataservices"
ORG_URL = "/api/1/organizations"
REUSE_URL = "/api/1/reuses"
COMMUNITY_RES_URL = "/api/1/datasets/community_resources"
DISCUSSION_URL = "/api/1/discussions"
POST_URL = "/api/1/posts"
SITE_URL = "/api/1/site"


DEFAULT_FIXTURE_FILE: str = str(
    pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "results.json"
)

DEFAULT_FIXTURES_RESULTS_FILENAME: str = "results.json"

UNWANTED_KEYS: dict[str, list[str]] = {
    "dataset": [
        "uri",
        "page",
        "last_update",
        "last_modified",
        "license",
        "spatial",
        "quality",
        "permissions",
    ],
    "resource": ["latest", "preview_url", "last_modified"],
    "organization": ["class", "page", "uri", "logo_thumbnail", "permissions"],
    "reuse": [
        "datasets",
        "image_thumbnail",
        "page",
        "uri",
        "owner",
        "permissions",
    ],
    "community": [
        "dataset",
        "owner",
        "latest",
        "last_modified",
        "preview_url",
        "permissions",
    ],
    # The owner is not the exported one: it is whoever owns the object being imported.
    "contact_point": ["organization", "owner"],
    "discussion": ["subject", "url", "self_web_url", "class", "permissions", "spam"],
    "discussion_message": ["permissions", "spam"],
    "user": ["uri", "page", "class", "avatar_thumbnail", "email"],
    "posted_by": ["uri", "page", "class", "avatar_thumbnail", "email"],
    "dataservice": [
        "datasets",
        "license",
        "owner",
        "self_api_url",
        "self_web_url",
        "permissions",
    ],
    "post": [
        "uri",
        "page",
        "image_thumbnail",
        "image",
        "last_modified",
        "datasets",
        "reuses",
        "owner",
        "permissions",
        "parent",
        "ancestors",
    ],
    "site": [
        "version",
        "settings",
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


def without_blocs(items: list[dict], removed: Callable[[dict], bool]) -> list[dict]:
    """Serialized blocs without the `removed` ones, at any depth.

    A container (section, accordion item) left empty only held removed blocs: it goes with
    them.
    """
    kept = []
    for item in items:
        if removed(item):
            continue
        emptied = False
        for key, value in item.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                item[key] = without_blocs(value, removed)
                emptied = emptied or not item[key]
        if not emptied:
            kept.append(item)
    return kept


def clean_blocs_for_generate(blocs: list[dict], resource_ids: set[str]) -> list[dict]:
    """Remove the blocs the fixtures could not import: those showing an object, as the
    fixtures don't hold them, and the explorers of a resource of a dataset not exported."""
    object_fields = {
        name
        for bloc_class in classes_by_parents.get(Bloc, set())
        for name, mongo_field in bloc_class._fields.items()
        if isinstance(mongo_field, ReferenceField)
    }

    def removed(bloc: dict) -> bool:
        if "resource_id" in bloc and bloc["resource_id"] not in resource_ids:
            return True
        return any(name in bloc for name in object_fields)

    return without_blocs(blocs, removed)


@cli.command()
@click.argument("data-source")
@click.argument("results-filename", default=DEFAULT_FIXTURES_RESULTS_FILENAME)
def generate_fixtures_file(data_source: str, results_filename: str) -> None:
    """Build sample fixture file (datasets, posts, site) from a remote udata instance."""
    results_file = pathlib.Path(results_filename)
    datasets_slugs = current_app.config["FIXTURE_DATASET_SLUGS"]
    json_datasets = []

    with click.progressbar(datasets_slugs, label="Fetching datasets") as bar:
        for slug in bar:
            json_fixture = {}

            url = f"{data_source}{DATASET_URL}/{slug}/"
            response = requests.get(url)
            if not response.ok:
                print(f"Got a status code {response.status_code} while getting {url}, skipping")
                continue
            json_dataset = response.json()
            json_dataset = remove_unwanted_keys(json_dataset, "dataset")
            json_resources = json_dataset.pop("resources")
            for resource in json_resources:
                remove_unwanted_keys(resource, "resource")
            if json_dataset["organization"] is None:
                json_owner = json_dataset.pop("owner")
                if json_owner:
                    json_owner = remove_unwanted_keys(json_owner, "user")
                    json_dataset["owner"] = json_owner["id"]
            else:
                json_org = json_dataset.pop("organization")
                json_org = requests.get(f"{data_source}{ORG_URL}/{json_org['id']}/").json()
                json_org = remove_unwanted_keys(json_org, "organization")
                json_fixture["organization"] = json_org
            json_fixture["resources"] = json_resources
            json_fixture["dataset"] = json_dataset

            json_reuses = requests.get(
                f"{data_source}{REUSE_URL}/?dataset={json_dataset['id']}"
            ).json()["data"]
            for reuse in json_reuses:
                remove_unwanted_keys(reuse, "reuse")
            json_fixture["reuses"] = json_reuses

            json_community = requests.get(
                f"{data_source}{COMMUNITY_RES_URL}/?dataset={json_dataset['id']}"
            ).json()["data"]
            for community_resource in json_community:
                remove_unwanted_keys(community_resource, "community")
            json_fixture["community_resources"] = json_community

            json_discussion = requests.get(
                f"{data_source}{DISCUSSION_URL}/?for={json_dataset['id']}"
            ).json()["data"]
            for discussion in json_discussion:
                remove_unwanted_keys(discussion, "discussion")
                for index, message in enumerate(discussion["discussion"]):
                    discussion["discussion"][index] = remove_unwanted_keys(
                        message, "discussion_message"
                    )

            json_fixture["discussions"] = json_discussion

            json_dataservices = requests.get(
                f"{data_source}{DATASERVICES_URL}/?dataset={json_dataset['id']}"
            ).json()["data"]
            for dataservice in json_dataservices:
                remove_unwanted_keys(dataservice, "dataservice")
            json_fixture["dataservices"] = json_dataservices

            json_datasets.append(json_fixture)

    resource_ids = {
        resource["id"] for fixture in json_datasets for resource in fixture["resources"]
    }

    # Fetch posts (detail endpoint to get blocs)
    print("Fetching posts...")
    json_posts_list = requests.get(f"{data_source}{POST_URL}/?page_size=20").json()["data"]
    json_posts = []
    for post_summary in json_posts_list:
        post_detail = requests.get(f"{data_source}{POST_URL}/{post_summary['slug']}/").json()
        remove_unwanted_keys(post_detail, "post")
        if "blocs" in post_detail:
            post_detail["blocs"] = clean_blocs_for_generate(post_detail["blocs"], resource_ids)
        json_posts.append(post_detail)

    # Fetch site (with blocs via X-Fields)
    print("Fetching site...")
    json_site = requests.get(f"{data_source}{SITE_URL}/", headers={"X-Fields": "{*}"}).json()
    remove_unwanted_keys(json_site, "site")
    for blocs_field in SITE_BLOCS_FIELDS:
        if blocs_field in json_site:
            json_site[blocs_field] = clean_blocs_for_generate(json_site[blocs_field], resource_ids)

    json_output = {
        "datasets": json_datasets,
        "posts": json_posts,
        "site": json_site,
    }

    with results_file.open("w") as f:
        json.dump(json_output, f, indent=2)
        print(f"Fixtures saved to file {results_filename}")


def get_or_create(data, key, model, factory):
    """Try getting the object from data[key]. If it doesn't exist yet, create it with the provided factory."""
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


def get_or_create_contact_point(data, owner):
    obj = ContactPoint.objects(id=data["id"]).first()
    if obj:
        # A contact point exported from one owner can be referenced by objects of another.
        return obj.for_owner(owner)
    data = remove_unwanted_keys(data, "contact_point")
    if not data.get("role"):
        data["role"] = "contact" if (data.get("email") or data.get("contact_form")) else "creator"
    return ContactPointFactory(**data, **ownership_filter(owner))


@cli.command()
@click.argument("source", default=DEFAULT_FIXTURE_FILE)
def import_fixtures(source):
    """Build sample fixture data (datasets, posts, site) from local or remote file."""
    if source.startswith("http"):
        response = requests.get(source)
        response.raise_for_status()
        json_fixtures = response.json()
    else:
        with open(source) as f:
            json_fixtures = json.load(f)

    # Import datasets
    with click.progressbar(json_fixtures["datasets"], label="Importing datasets") as bar:
        for fixture in bar:
            user = UserFactory()
            dataset = fixture["dataset"]
            dataset = remove_unwanted_keys(dataset, "dataset")
            # The exported ownership is dropped rather than listed in UNWANTED_KEYS, which is
            # applied at export time, while `organization` is still needed to build the fixture.
            dataset.pop("organization", None)
            dataset.pop("owner", None)
            # The owner comes first: contact points belong to whoever owns the dataset.
            if fixture.get("organization"):
                organization = fixture["organization"]
                organization["members"] = [
                    Member(user=get_or_create_user(member), role=member["role"])
                    for member in organization["members"]
                ]
                fixture["organization"] = organization
                owner = get_or_create_organization(fixture)
            else:
                owner = user
            dataset["contact_points"] = [
                get_or_create_contact_point(contact_point, owner)
                for contact_point in dataset.get("contact_points") or []
            ]
            dataset = DatasetFactory(**dataset, **ownership_filter(owner))
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
                    message = remove_unwanted_keys(message, "discussion_message")
                    message["posted_by"] = get_or_create(message, "posted_by", User, UserFactory)
                discussion["discussion"] = [
                    MessageDiscussionFactory(**remove_unwanted_keys(message, "discussion_message"))
                    for message in discussion["discussion"]
                ]
                discussion["user"] = get_or_create_user(discussion)
                DiscussionFactory(**discussion, subject=dataset)
            for dataservice in fixture["dataservices"]:
                dataservice = remove_unwanted_keys(dataservice, "dataservice")
                # An exported dataservice without an organization belongs to the fixture
                # user, like the dataset above: a contact point needs an owner to belong to.
                dataservice_owner = get_or_create_organization(dataservice) or user
                dataservice.pop("organization", None)
                dataservice["contact_points"] = [
                    get_or_create_contact_point(contact_point, dataservice_owner)
                    for contact_point in dataservice.get("contact_points") or []
                ]
                DataserviceFactory(
                    **dataservice, datasets=[dataset], **ownership_filter(dataservice_owner)
                )

    # Import posts and the site last: their blocs are checked as the API would, and an
    # explorer bloc requires the resource it explores.
    for post_data in json_fixtures.get("posts", []):
        post_data = remove_unwanted_keys(post_data, "post")
        user = UserFactory()
        blocs = patch(Post(), {"blocs": post_data.pop("blocs", [])}).blocs
        if not Post.objects(id=post_data["id"]).first():
            PostFactory(
                **post_data,
                owner=user,
                blocs=blocs,
                datasets=[],
                reuses=[],
            )

    site_data = json_fixtures.get("site")
    if site_data:
        site_data = remove_unwanted_keys(site_data, "site")
        blocs = {field: site_data.pop(field) for field in SITE_BLOCS_FIELDS if field in site_data}
        site = patch(Site(), blocs)
        if not Site.objects(id=site_data["id"]).first():
            SiteFactory(**site_data, **{field: getattr(site, field) for field in blocs})
