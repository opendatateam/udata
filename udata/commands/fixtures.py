"""Commands to generate and import fixtures locally.

When "downloading" (generating) the fixtures, save the json as is.
When "importing" the fixtures, massage them so they can be loaded properly.
"""

import json
import logging
import pathlib
from importlib import resources

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
from udata.core.pages.factories import PageFactory
from udata.core.pages.models import (
    AccordionItemBloc,
    AccordionListBloc,
    DataservicesListBloc,
    DatasetsListBloc,
    HeroBloc,
    LinkInBloc,
    LinksListBloc,
    MarkdownBloc,
    Page,
    ReusesListBloc,
)
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
PAGE_URL = "/api/1/pages"


DEFAULT_FIXTURE_FILE: str = str(resources.files("udata") / "fixtures" / "results.json")

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
    "organization": ["class", "page", "uri", "logo_thumbnail"],
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
    "discussion": ["subject", "url", "self_web_url", "class", "permissions"],
    "discussion_message": ["permissions"],
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
    ],
    "page": [
        "permissions",
        "owner",
        "organization",
        "last_modified",
        "created_at",
    ],
    "site": [
        "version",
        "settings",
    ],
}

BLOC_CLASSES = {
    "DatasetsListBloc": DatasetsListBloc,
    "ReusesListBloc": ReusesListBloc,
    "DataservicesListBloc": DataservicesListBloc,
    "LinksListBloc": LinksListBloc,
    "HeroBloc": HeroBloc,
    "MarkdownBloc": MarkdownBloc,
    "AccordionListBloc": AccordionListBloc,
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


def clean_bloc_for_generate(bloc: dict) -> dict:
    """Strip expanded reference objects from blocs, keep only structural content."""
    for ref_field in ("datasets", "reuses", "dataservices"):
        bloc.pop(ref_field, None)
    if bloc.get("items"):
        for item in bloc["items"]:
            for sub_bloc in item.get("content", []):
                clean_bloc_for_generate(sub_bloc)
    return bloc


def create_bloc_from_dict(data: dict):
    """Convert a bloc dict from the fixture JSON into a MongoEngine EmbeddedDocument."""
    cls_name = data.pop("class", None)
    bloc_class = BLOC_CLASSES.get(cls_name)
    if not bloc_class:
        return None

    if cls_name == "LinksListBloc" and "links" in data:
        data["links"] = [LinkInBloc(**link) for link in data["links"]]
    elif cls_name == "AccordionListBloc" and "items" in data:
        items = []
        for item in data["items"]:
            content = [create_bloc_from_dict(b) for b in item.get("content", [])]
            items.append(AccordionItemBloc(title=item["title"], content=[c for c in content if c]))
        data["items"] = items

    return bloc_class(**data)


@cli.command()
@click.argument("data-source")
@click.argument("results-filename", default=DEFAULT_FIXTURES_RESULTS_FILENAME)
def generate_fixtures_file(data_source: str, results_filename: str) -> None:
    """Build sample fixture file (datasets, posts, pages, site) from a remote udata instance."""
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

    # Fetch posts
    print("Fetching posts...")
    json_posts = requests.get(f"{data_source}{POST_URL}/?page_size=20").json()["data"]
    page_ids = set()
    for post in json_posts:
        remove_unwanted_keys(post, "post")
        if post.get("content_as_page"):
            content_as_page = post["content_as_page"]
            if isinstance(content_as_page, dict):
                page_ids.add(content_as_page["id"])
                post["content_as_page"] = content_as_page["id"]
            else:
                page_ids.add(content_as_page)

    # Fetch site
    print("Fetching site...")
    json_site = requests.get(f"{data_source}{SITE_URL}/").json()
    remove_unwanted_keys(json_site, "site")
    for page_field in ("datasets_page", "reuses_page", "dataservices_page"):
        if json_site.get(page_field):
            page_ids.add(json_site[page_field])

    # Fetch all referenced pages
    json_pages = []
    for page_id in page_ids:
        response = requests.get(f"{data_source}{PAGE_URL}/{page_id}/")
        if response.ok:
            page = response.json()
            remove_unwanted_keys(page, "page")
            for bloc in page.get("blocs", []):
                clean_bloc_for_generate(bloc)
            json_pages.append(page)
        else:
            print(
                f"Got a status code {response.status_code} while getting page {page_id}, skipping"
            )

    json_output = {
        "datasets": json_datasets,
        "posts": json_posts,
        "pages": json_pages,
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


def get_or_create_contact_point(data):
    obj = ContactPoint.objects(id=data["id"]).first()
    if not obj:
        if not data.get("role"):
            data["role"] = (
                "contact" if (data.get("email") or data.get("contact_form")) else "creator"
            )
        obj = ContactPointFactory(**data)
    return obj


@cli.command()
@click.argument("source", default=DEFAULT_FIXTURE_FILE)
def import_fixtures(source):
    """Build sample fixture data (datasets, posts, pages, site) from local or remote file."""
    if source.startswith("http"):
        response = requests.get(source)
        response.raise_for_status()
        json_fixtures = response.json()
    else:
        with open(source) as f:
            json_fixtures = json.load(f)

    # Import pages first (site references them)
    for page_data in json_fixtures.get("pages", []):
        page_data = remove_unwanted_keys(page_data, "page")
        blocs = [create_bloc_from_dict(b) for b in page_data.pop("blocs", [])]
        blocs = [b for b in blocs if b is not None]
        if not Page.objects(id=page_data["id"]).first():
            PageFactory(**page_data, blocs=blocs)

    # Import site
    site_data = json_fixtures.get("site")
    if site_data:
        site_data = remove_unwanted_keys(site_data, "site")
        for page_field in ("datasets_page", "reuses_page", "dataservices_page"):
            if site_data.get(page_field):
                site_data[page_field] = Page.objects(id=site_data[page_field]).first()
        if not Site.objects(id=site_data["id"]).first():
            SiteFactory(**site_data)

    # Import datasets
    with click.progressbar(json_fixtures["datasets"], label="Importing datasets") as bar:
        for fixture in bar:
            user = UserFactory()
            dataset = fixture["dataset"]
            dataset = remove_unwanted_keys(dataset, "dataset")
            contact_points = []
            for contact_point in dataset.get("contact_points") or []:
                contact_points.append(get_or_create_contact_point(contact_point))
            dataset["contact_points"] = contact_points
            if fixture.get("organization"):
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
                contact_points = []
                for contact_point in dataservice.get("contact_points") or []:
                    contact_points.append(get_or_create_contact_point(contact_point))
                dataservice["contact_points"] = contact_points
                dataservice["organization"] = get_or_create_organization(dataservice)
                DataserviceFactory(**dataservice, datasets=[dataset])

    # Import posts
    for post_data in json_fixtures.get("posts", []):
        post_data = remove_unwanted_keys(post_data, "post")
        user = UserFactory()
        content_as_page = None
        if post_data.get("content_as_page"):
            content_as_page = Page.objects(id=post_data.pop("content_as_page")).first()
        if not Post.objects(id=post_data["id"]).first():
            PostFactory(**post_data, owner=user, content_as_page=content_as_page)
