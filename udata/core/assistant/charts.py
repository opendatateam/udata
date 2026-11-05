"""Declarative chart tool inputs, validation and conversion to the chart model."""

from typing import Literal

from pydantic import BaseModel, Field

from udata.core.assistant.data_query import Aggregate, GenericFilter, filter_columns

NUMERIC_TYPES = frozenset({"int", "float"})


class XAxisInput(BaseModel):
    column_x: str
    type: Literal["discrete", "continuous"]
    sort_x_by: Literal["axis_x", "axis_y"] = "axis_x"
    sort_x_direction: Literal["asc", "desc"] = "asc"
    limit: int | None = Field(None, ge=1, le=50)


class SeriesInput(BaseModel):
    column_y: str
    aggregate_y: Aggregate | None = None


class YAxisInput(BaseModel):
    label: str | None = None
    unit: str | None = Field(None, max_length=20)
    unit_position: Literal["prefix", "suffix"] | None = None
    min: float | None = None
    max: float | None = None


class CreateChartInput(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    type: Literal["line", "histogram"]
    x_axis: XAxisInput
    series: list[SeriesInput] = Field(min_length=1, max_length=4)
    filters: GenericFilter | None = None
    y_axis: YAxisInput | None = None


class UpdateChartInput(BaseModel):
    title: str | None = Field(None, min_length=1)
    description: str | None = None
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
        column = columns.get(name)
        if isinstance(column, dict) and isinstance(column.get("python_type"), str):
            result[name] = column["python_type"]
    return result


def validate_create(config: CreateChartInput, columns: dict[str, str]) -> list[str]:
    errors: list[str] = []

    def unknown(name: str) -> None:
        if name not in columns:
            errors.append(f"Colonne inconnue : {name}.")

    unknown(config.x_axis.column_x)
    for series in config.series:
        unknown(series.column_y)
    for name in sorted(filter_columns(config.filters)):
        unknown(name)
    for series in config.series:
        column_type = columns.get(series.column_y)
        if column_type is None or column_type in NUMERIC_TYPES:
            continue
        if series.aggregate_y is None:
            errors.append(f"La série {series.column_y} doit être numérique ou agrégée par count.")
        elif series.aggregate_y != "count":
            errors.append(
                f"L'agrégat {series.aggregate_y} demande une colonne numérique : "
                f"{series.column_y} est de type {column_type}."
            )
    return list(dict.fromkeys(errors))


def validate_update(patch: UpdateChartInput) -> list[str]:
    fields = patch.model_fields_set
    empty_y_axis = fields == {"y_axis"} and (
        patch.y_axis is None or not patch.y_axis.model_fields_set
    )
    if not fields or empty_y_axis:
        return ["Au moins une modification est requise."]
    return []


def to_chart_output(config: CreateChartInput, resource_id: str) -> dict:
    filters = config.filters.model_dump(by_alias=True) if config.filters else None
    y_axis = config.y_axis or YAxisInput()
    return {
        "title": config.title,
        "description": config.description,
        "x_axis": config.x_axis.model_dump(),
        "y_axis": y_axis.model_dump(),
        "series": [
            {
                "type": config.type,
                "column_y": s.column_y,
                "aggregate_y": s.aggregate_y,
                "resource_id": resource_id,
                "column_x_name_override": None,
                "filters": filters,
            }
            for s in config.series
        ],
    }


def to_update_output(patch: UpdateChartInput) -> dict:
    return patch.model_dump(exclude_unset=True)
