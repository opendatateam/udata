"""Conversion of blocs stored in the format that predates sections and grids.

Blocs used to sit directly in a blocs field, each with an optional title, and list several
datasets/reuses/dataservices at once. They now sit in sections, titles are `TitleBloc`s and
objects are shown one per bloc, laid out by a `GridBloc`. Used by the
`2026-10-21-blocs-sections` migration. cdata reads the legacy format the same way until the
migration ran (`normalizeBlocs`), so both must stay in sync.

Works on blocs as stored in MongoDB (`_cls`, `_id`), so that it does not depend on the
legacy classes it replaces.
"""

import uuid
from collections.abc import Callable
from typing import NamedTuple


class LegacyList(NamedTuple):
    list_field: str
    # The bloc showing one of the listed objects, and its reference field
    object_cls: str
    reference_field: str
    # Width of the cell holding each object in the grid replacing the list
    width: str


LEGACY_LISTS = {
    "DatasetsListBloc": LegacyList("datasets", "DatasetBloc", "dataset", "1/2"),
    "DataservicesListBloc": LegacyList("dataservices", "DataserviceBloc", "dataservice", "1/2"),
    "ReusesListBloc": LegacyList("reuses", "ReuseBloc", "reuse", "1/3"),
}

# Legacy bloc -> (title field, secondary text field)
LEGACY_TITLES = {
    "DatasetsListBloc": ("title", "subtitle"),
    "DataservicesListBloc": ("title", "subtitle"),
    "ReusesListBloc": ("title", "subtitle"),
    "MarkdownBloc": ("title", "subtitle"),
    "LinksListBloc": ("title", "subtitle"),
    "ExploreBloc": ("title", "subtitle"),
    "AccordionListBloc": ("title", "description"),
}


def _new_id() -> str:
    return str(uuid.uuid4())


def _upgrade_content(bloc: dict, keep_reference: Callable[[object], bool]) -> list[dict]:
    """Convert a legacy bloc into the blocs it becomes inside a section."""
    cls = bloc["_cls"]
    upgraded = []

    if cls in LEGACY_TITLES:
        title_field, secondary_field = LEGACY_TITLES[cls]
        title = bloc.pop(title_field, None)
        secondary = bloc.pop(secondary_field, None)
        has_title = bool(title and title.strip())
        has_secondary = bool(secondary and secondary.strip())
        if has_title:
            title_bloc = {"_id": _new_id(), "_cls": "TitleBloc", "title": title}
            if has_secondary:
                title_bloc["subtitle"] = secondary
            upgraded.append(title_bloc)
        elif has_secondary:
            # A `TitleBloc` needs a title: a lone subtitle is kept as text.
            upgraded.append({"_id": _new_id(), "_cls": "MarkdownBloc", "content": secondary})

    if cls in LEGACY_LISTS:
        legacy = LEGACY_LISTS[cls]
        cells = [
            {
                "_id": _new_id(),
                "width": legacy.width,
                "blocs": [
                    {"_id": _new_id(), "_cls": legacy.object_cls, legacy.reference_field: ref}
                ],
            }
            for ref in bloc.get(legacy.list_field) or []
            if keep_reference(ref)
        ]
        if cells:
            upgraded.append({"_id": _new_id(), "_cls": "GridBloc", "cells": cells})
    elif cls == "AccordionListBloc":
        for item in bloc.get("items") or []:
            item["content"] = [
                upgraded_bloc
                for content_bloc in item.get("content") or []
                for upgraded_bloc in _upgrade_content(content_bloc, keep_reference)
            ]
        upgraded.append(bloc)
    else:
        upgraded.append(bloc)

    return upgraded


def upgrade_legacy_blocs(
    blocs: list[dict], keep_reference: Callable[[object], bool] = lambda _ref: True
) -> list[dict]:
    """Return the blocs of a blocs field in the current format.

    Each legacy bloc gets its own section: they were each drawn on their own background band,
    which is now the section's. Blocs already in the current format are left untouched, so
    upgrading twice gives the same result.

    `keep_reference` filters the objects of the legacy lists: one that no longer exists must
    not become a bloc, whose reference is required.
    """
    return [
        bloc
        if bloc["_cls"] in ("HeroBloc", "SectionBloc")
        else {
            "_id": _new_id(),
            "_cls": "SectionBloc",
            "blocs": _upgrade_content(bloc, keep_reference),
        }
        for bloc in blocs
    ]


def legacy_references(blocs: list[dict]) -> set:
    """The objects listed by the legacy list blocs, at the top level and in accordions."""
    references = set()
    for bloc in blocs:
        if bloc.get("_cls") in LEGACY_LISTS:
            references.update(bloc.get(LEGACY_LISTS[bloc["_cls"]].list_field) or [])
        for item in bloc.get("items") or []:
            references |= legacy_references(item.get("content") or [])
    return references
