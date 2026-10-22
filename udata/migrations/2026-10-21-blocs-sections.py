"""
Move the blocs of posts, organizations and the site to sections and title blocs.

Blocs used to sit directly in a blocs field, each with an optional title, and list several
datasets/reuses/dataservices at once. Each top-level bloc now goes into its own section, its
title (or description for an accordion) becomes a `TitleBloc`, and a list becomes one bloc per
object, side by side through their width. A hero becomes a colored section, and a list of
links is split into a text, the links and a button. cdata reads the legacy format the same
way until this migration ran (`normalizeBlocs`), so both must stay in sync.

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


# The blocs holding a `title`, with a text under it: their `subtitle`, or the `description`
# of an accordion. Both become a `TitleBloc`.
LEGACY_TITLED = {*LEGACY_LISTS, "MarkdownBloc", "LinksListBloc", "ExploreBloc", "AccordionListBloc"}


def new_id() -> str:
    return str(uuid.uuid4())


def upgrade_content(bloc: dict) -> list[dict]:
    """Convert a legacy bloc into the blocs it becomes inside a section."""
    cls = bloc["_cls"]
    upgraded = []

    if cls in LEGACY_TITLED:
        title = bloc.pop("title", None)
        secondary = bloc.pop("description" if cls == "AccordionListBloc" else "subtitle", None)
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
    elif cls == "LinksListBloc":
        # Split into a text, the links and a button, which keep their places: the paragraph
        # on the left of the links with the button under it, or the button under the links.
        paragraph = bloc.pop("paragraph", None)
        button = button_bloc(bloc.pop("main_link_title", None), bloc.pop("main_link_url", None))
        width = "1/2" if paragraph and paragraph.strip() else None
        if width:
            upgraded.append(
                {"_id": new_id(), "_cls": "MarkdownBloc", "width": width, "content": paragraph}
            )
        upgraded.append({**bloc, "width": width} if width else bloc)
        if button:
            upgraded.append({**button, "width": width} if width else button)
    elif cls == "HeroBloc":
        # A hero inside an accordion item, which the API accepted for a few days (v14.7.0 and
        # v14.7.1): its title and its button, an item having no background of its own.
        upgraded.extend(hero_blocs(bloc))
    elif cls == "AccordionListBloc":
        for item in bloc.get("items") or []:
            item.setdefault("_id", new_id())
            item["content"] = [
                upgraded_bloc
                for content_bloc in item.get("content") or []
                for upgraded_bloc in upgrade_content(content_bloc)
            ]
        upgraded.append(bloc)
    else:
        upgraded.append(bloc)

    return upgraded


def button_bloc(title: str | None, url: str | None) -> dict | None:
    """The button of a legacy main link, which was only shown with both a title and a URL."""
    if not (title and title.strip() and url and url.strip()):
        return None
    return {"_id": new_id(), "_cls": "ButtonBloc", "title": title, "url": url}


def hero_blocs(hero: dict) -> list[dict]:
    """The title of a hero, its description as subtitle, and its button."""
    blocs = [{"_id": new_id(), "_cls": "TitleBloc", "title": hero["title"]}]
    if (description := hero.get("description")) and description.strip():
        blocs[0]["subtitle"] = description
    if button := button_bloc(hero.get("main_link_title"), hero.get("main_link_url")):
        blocs.append(button)
    return blocs


def upgrade_hero(hero: dict, colored: bool) -> dict:
    """A hero becomes a section of its color holding its title and its button.

    Without a color, the hero was drawn in the primary one. An organization page has no
    colored section (`check_no_colored_sections`): there, the section keeps a neutral
    background.
    """
    section = {"_id": hero["_id"], "_cls": "SectionBloc", "blocs": hero_blocs(hero)}
    if colored:
        section["color"] = hero.get("color") or "primary"
    return section


def upgrade_legacy_blocs(blocs: list[dict], colored: bool = True) -> list[dict]:
    """Return the blocs of a blocs field in the current format.

    Each legacy bloc gets its own section: they were each drawn on their own background band,
    which is now the section's. Blocs already in the current format are left untouched, so
    upgrading twice gives the same result. `colored` tells whether the sections of the field
    can have a color. A legacy bloc showing nothing (an empty list without a title) is dropped:
    a section cannot be empty.
    """
    upgraded = []
    for bloc in blocs:
        if bloc["_cls"] == "SectionBloc":
            upgraded.append(bloc)
        elif bloc["_cls"] == "HeroBloc":
            upgraded.append(upgrade_hero(bloc, colored))
        elif content := upgrade_content(bloc):
            upgraded.append({"_id": new_id(), "_cls": "SectionBloc", "blocs": content})
    return upgraded


def migrate(db):
    for model, blocs_fields in (
        (Post, ("blocs",)),
        (Organization, ("presentation_blocs",)),
        (Site, SITE_BLOCS_FIELDS),
    ):
        collection = model._get_collection()
        for blocs_field in blocs_fields:
            # Already upgraded blocs fields only hold sections.
            legacy = {blocs_field: {"$elemMatch": {"_cls": {"$ne": "SectionBloc"}}}}
            count = 0
            for doc in collection.find(legacy, {blocs_field: 1}):
                blocs = upgrade_legacy_blocs(doc[blocs_field], colored=model is not Organization)
                collection.update_one({"_id": doc["_id"]}, {"$set": {blocs_field: blocs}})
                count += 1
            log.info(f"Upgraded {model.__name__}.{blocs_field} on {count} documents")
