"""Declarative chart tool inputs, validation and conversion to the chart model."""

import copy
from collections.abc import Iterable
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from udata.core.assistant.data_query import (
    PAGE_SIZE,
    Aggregate,
    GenericFilter,
    filter_columns,
    filter_errors,
)

NUMERIC_TYPES = frozenset({"int", "float"})

# A chart needs both to be saved (`Chart.title` and `Chart.description` are required).
EMPTY_TEXT_ERRORS = {
    "title": "Le titre est obligatoire et ne peut pas être vide.",
    "description": "La description est obligatoire et ne peut pas être vide.",
}

StrippedText = Annotated[str, StringConstraints(strip_whitespace=True)]


class XAxisInput(BaseModel):
    column_x: str = Field(description="Colonne de l'axe X")
    type: Literal["discrete", "continuous"] = Field(
        description="discrete pour des catégories, continuous pour des dates ou nombres ordonnés"
    )
    sort_x_by: Literal["axis_x", "axis_y"] = Field(
        "axis_x", description="axis_x : trier par X ; axis_y : trier par la valeur Y"
    )
    sort_x_direction: Literal["asc", "desc"] = Field("asc", description="Sens du tri")
    limit: int | None = Field(
        None,
        ge=1,
        le=PAGE_SIZE,
        description=f"Nombre de valeurs affichées après le tri (1 à {PAGE_SIZE})",
    )


class SeriesInput(BaseModel):
    column_y: str
    aggregate_y: Aggregate | None = None


class YAxisInput(BaseModel):
    label: str | None = Field(None, description="Libellé de l'axe Y")
    unit: str | None = Field(None, max_length=20, description="Unité des valeurs")
    unit_position: Literal["prefix", "suffix"] | None = Field(None, description="prefix ou suffix")
    min: float | None = Field(None, description="Borne minimale de l'axe Y")
    max: float | None = Field(None, description="Borne maximale de l'axe Y")


class CreateChartInput(BaseModel):
    title: StrippedText = Field(description="Titre du graphique, non vide")
    description: StrippedText = Field(description="Description du graphique, non vide")
    type: Literal["line", "histogram"]
    x_axis: XAxisInput
    series: list[SeriesInput] = Field(min_length=1, max_length=4)
    filters: GenericFilter | None = None
    y_axis: YAxisInput | None = None


class UpdateChartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: StrippedText | None = None
    description: StrippedText | None = None
    type: Literal["line", "histogram"] | None = None
    y_axis: YAxisInput | None = None


def profile_columns(profile: dict) -> dict[str, str]:
    """`{name: python_type}` from an api-tabular profile, in `header` order."""
    details = profile.get("profile") if isinstance(profile, dict) else None
    if not isinstance(details, dict):
        return {}
    columns = details.get("columns")
    if not isinstance(columns, dict):
        return {}
    header = details.get("header")
    names = header if isinstance(header, list) else list(columns)
    result = {}
    for name in names:
        if not isinstance(name, str):
            continue
        column = columns.get(name)
        if isinstance(column, dict) and isinstance(column.get("python_type"), str):
            result[name] = column["python_type"]
    return result


def aggregate_error(column: str, aggregate: Aggregate, column_type: str | None) -> str | None:
    """Refusal of an aggregate other than count on a column the profile does not type as numeric."""
    if aggregate == "count" or column_type is None or column_type in NUMERIC_TYPES:
        return None
    return (
        f"L'agrégat {aggregate} demande une colonne numérique : {column} est de type {column_type}."
    )


def query_aggregate_error(column: str, aggregate: Aggregate, column_type: str | None) -> str | None:
    """Like `aggregate_error`, but min and max order any type (e.g. the latest date)."""
    if aggregate in ("min", "max"):
        return None
    return aggregate_error(column, aggregate, column_type)


def unknown_column_errors(names: Iterable[str | None], known: dict[str, str]) -> list[str]:
    """One French error per distinct unknown column, in order; empty names are skipped."""
    unknown = dict.fromkeys(name for name in names if name and name not in known)
    return [f"Colonne inconnue : {name}." for name in unknown]


def _empty_text_errors(values: dict[str, str | None]) -> list[str]:
    return [EMPTY_TEXT_ERRORS[name] for name, value in values.items() if value == ""]


def validate_create(config: CreateChartInput, columns: dict[str, str]) -> list[str]:
    errors = _empty_text_errors({"title": config.title, "description": config.description})
    errors += unknown_column_errors(
        [
            config.x_axis.column_x,
            # A count series counts the X column: its column_y is never read.
            *(series.column_y for series in config.series if series.aggregate_y != "count"),
            *sorted(filter_columns(config.filters)),
        ],
        columns,
    )
    for series in config.series:
        if series.aggregate_y == "count":
            continue
        column_type = columns.get(series.column_y)
        if series.aggregate_y is not None:
            if error := aggregate_error(series.column_y, series.aggregate_y, column_type):
                errors.append(error)
        elif column_type is not None and column_type not in NUMERIC_TYPES:
            errors.append(f"La série {series.column_y} doit être numérique ou agrégée par count.")
    errors.extend(filter_errors(config.filters))
    return list(dict.fromkeys(errors))


def validate_update(patch: UpdateChartInput) -> list[str]:
    if errors := _empty_text_errors({"title": patch.title, "description": patch.description}):
        return errors
    if not to_update_output(patch):
        return ["Au moins une modification est requise."]
    return []


def to_chart_output(config: CreateChartInput, resource_id: str) -> dict:
    """Chart of the frontend model; a count series has the X column as `column_y`.

    The chart form reads a series as a count when `column_y` is `column_x`. Every
    count series is then the same: only the first one is kept, in order.
    """
    filters = config.filters.model_dump(by_alias=True) if config.filters else None
    y_axis = config.y_axis or YAxisInput()
    first_count = next((s for s in config.series if s.aggregate_y == "count"), None)
    series = [s for s in config.series if s.aggregate_y != "count" or s is first_count]
    return {
        "title": config.title,
        "description": config.description,
        "x_axis": config.x_axis.model_dump(),
        "y_axis": y_axis.model_dump(),
        "series": [
            {
                "type": config.type,
                "column_y": config.x_axis.column_x if s.aggregate_y == "count" else s.column_y,
                "aggregate_y": s.aggregate_y,
                "resource_id": resource_id,
                "column_x_name_override": None,
                "filters": copy.deepcopy(filters),
            }
            for s in series
        ],
    }


def to_update_output(patch: UpdateChartInput) -> dict:
    """Provided fields only; top-level nulls mean "leave unchanged" and are dropped.

    Inside `y_axis`, an explicit null is kept: it clears that field.
    """
    out = {k: v for k, v in patch.model_dump(exclude_unset=True).items() if v is not None}
    if "y_axis" in out and not out["y_axis"]:
        del out["y_axis"]
    return out
