"""Conversion of blocs stored in the format that predates sections and grids.

Blocs used to sit directly in a blocs field, each with an optional title, and list several
datasets/reuses/dataservices at once. They now sit in sections, titles are `TitleBloc`s and
objects are shown one per bloc, laid out by a `GridBloc`. Used by the
`2026-10-21-blocs-sections` migration and by `import_fixtures` for fixture files exported
before it. cdata reads the legacy format the same way until the migration ran
(`normalizeBlocs`), so both must stay in sync.

Works on blocs as stored in MongoDB (`_cls`, `_id`), so that it does not depend on the
legacy classes it replaces.
"""

import uuid

# Legacy list bloc -> (list field, bloc class for one object, its reference field, cell width)
LEGACY_LISTS = {
    "DatasetsListBloc": ("datasets", "DatasetBloc", "dataset", "1/2"),
    "DataservicesListBloc": ("dataservices", "DataserviceBloc", "dataservice", "1/2"),
    "ReusesListBloc": ("reuses", "ReuseBloc", "reuse", "1/3"),
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


def _upgrade_content(bloc: dict) -> list[dict]:
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
        list_field, object_cls, reference_field, width = LEGACY_LISTS[cls]
        cells = [
            {
                "_id": _new_id(),
                "width": width,
                "blocs": [{"_id": _new_id(), "_cls": object_cls, reference_field: ref}],
            }
            for ref in bloc.get(list_field) or []
        ]
        if cells:
            upgraded.append({"_id": _new_id(), "_cls": "GridBloc", "cells": cells})
    elif cls == "AccordionListBloc":
        for item in bloc.get("items") or []:
            item["content"] = [
                upgraded_bloc
                for content_bloc in item.get("content") or []
                for upgraded_bloc in _upgrade_content(content_bloc)
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
        else {"_id": _new_id(), "_cls": "SectionBloc", "blocs": _upgrade_content(bloc)}
        for bloc in blocs
    ]
