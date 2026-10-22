"""
Move the blocs of posts, organizations and the site to sections and title blocs.

Blocs used to sit directly in a blocs field, each with an optional title, and list several
datasets/reuses/dataservices at once. Each top-level bloc now goes into its own section, its
title (or description for an accordion) becomes a `TitleBloc`, and a list becomes one bloc per
object, side by side through their width. cdata reads the legacy format the same way until
this migration ran (`normalizeBlocs`), so both must stay in sync.

Works on blocs as stored in MongoDB (`_cls`, `_id`), so that it does not depend on the legacy
classes it replaces. An object deleted since it was listed becomes a bloc all the same: the
API leaves out the blocs of objects that no longer exist.
"""

import logging
import uuid
from typing import NamedTuple

from udata.core.edito_blocs.models import SITE_BLOCS_FIELDS
from udata.core.organization.models import Organization
from udata.core.post.models import Post
from udata.core.site.models import Site

log = logging.getLogger(__name__)


class LegacyList(NamedTuple):
    list_field: str
    # The bloc showing one of the listed objects, and its reference field
    object_cls: str
    reference_field: str
    # Width of each object bloc, so that they keep the columns of the list they replace
    width: str


LEGACY_LISTS = {
    "DatasetsListBloc": LegacyList("datasets", "DatasetBloc", "dataset", "1/2"),
    "DataservicesListBloc": LegacyList("dataservices", "DataserviceBloc", "dataservice", "1/2"),
    "ReusesListBloc": LegacyList("reuses", "ReuseBloc", "reuse", "1/3"),
}


class LegacyTitle(NamedTuple):
    title_field: str
    # The text under the title: the subtitle of the `TitleBloc` replacing them
    secondary_field: str


LEGACY_TITLES = {
    "DatasetsListBloc": LegacyTitle("title", "subtitle"),
    "DataservicesListBloc": LegacyTitle("title", "subtitle"),
    "ReusesListBloc": LegacyTitle("title", "subtitle"),
    "MarkdownBloc": LegacyTitle("title", "subtitle"),
    "LinksListBloc": LegacyTitle("title", "subtitle"),
    "ExploreBloc": LegacyTitle("title", "subtitle"),
    "AccordionListBloc": LegacyTitle("title", "description"),
}


def new_id() -> str:
    return str(uuid.uuid4())


def upgrade_content(bloc: dict) -> list[dict]:
    """Convert a legacy bloc into the blocs it becomes inside a section."""
    cls = bloc["_cls"]
    upgraded = []

    if cls in LEGACY_TITLES:
        legacy_title = LEGACY_TITLES[cls]
        title = bloc.pop(legacy_title.title_field, None)
        secondary = bloc.pop(legacy_title.secondary_field, None)
        has_title = bool(title and title.strip())
        has_secondary = bool(secondary and secondary.strip())
        if has_title:
            title_bloc = {"_id": new_id(), "_cls": "TitleBloc", "title": title}
            if has_secondary:
                title_bloc["subtitle"] = secondary
            upgraded.append(title_bloc)
        elif has_secondary:
            # A `TitleBloc` needs a title: a lone subtitle is kept as text.
            upgraded.append({"_id": new_id(), "_cls": "MarkdownBloc", "content": secondary})

    if cls in LEGACY_LISTS:
        legacy = LEGACY_LISTS[cls]
        upgraded.extend(
            {
                "_id": new_id(),
                "_cls": legacy.object_cls,
                "width": legacy.width,
                legacy.reference_field: ref,
            }
            for ref in bloc.get(legacy.list_field) or []
        )
    elif cls == "AccordionListBloc":
        for item in bloc.get("items") or []:
            item["content"] = [
                upgraded_bloc
                for content_bloc in item.get("content") or []
                for upgraded_bloc in upgrade_content(content_bloc)
            ]
        upgraded.append(bloc)
    else:
        upgraded.append(bloc)

    return upgraded


def upgrade_legacy_blocs(blocs: list[dict]) -> list[dict]:
    """Return the blocs of a blocs field in the current format.

    Each legacy bloc gets its own section: they were each drawn on their own background band,
    which is now the section's. Blocs already in the current format are left untouched, so
    upgrading twice gives the same result.
    """
    return [
        bloc
        if bloc["_cls"] in ("HeroBloc", "SectionBloc")
        else {"_id": new_id(), "_cls": "SectionBloc", "blocs": upgrade_content(bloc)}
        for bloc in blocs
    ]


def migrate(db):
    for model, blocs_fields in (
        (Post, ("blocs",)),
        (Organization, ("presentation_blocs",)),
        (Site, SITE_BLOCS_FIELDS),
    ):
        collection = model._get_collection()
        for blocs_field in blocs_fields:
            # Already upgraded blocs fields only hold sections and heroes.
            legacy = {blocs_field: {"$elemMatch": {"_cls": {"$nin": ["SectionBloc", "HeroBloc"]}}}}
            count = 0
            for doc in collection.find(legacy, {blocs_field: 1}):
                blocs = upgrade_legacy_blocs(doc[blocs_field])
                collection.update_one({"_id": doc["_id"]}, {"$set": {blocs_field: blocs}})
                count += 1
            log.info(f"Upgraded {model.__name__}.{blocs_field} on {count} documents")
