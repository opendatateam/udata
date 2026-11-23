"""Declarative chart tool inputs, validation and conversion to the chart model."""

import copy
from collections.abc import Iterable
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from udata.core.assistant.data_query import (
    Aggregate,
    GenericFilter,
    filter_columns,
    filter_errors,
    model_choices,
)
from udata.core.visualizations.models import DataSeries, XAxis, YAxis

NUMERIC_TYPES = frozenset({"int", "float"})

# Never empty: a chart needs a title and a description to be saved.
StrippedText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ChartType = model_choices(DataSeries.type)
AxisType = model_choices(XAxis.type)
SortBy = model_choices(XAxis.sort_x_by)
SortDirection = model_choices(XAxis.sort_x_direction)
UnitPosition = model_choices(YAxis.unit_position)


class XAxisInput(BaseModel):
    column_x: str = Field(description="Column of the X axis")
    type: AxisType = Field(
        description="discrete for categories, continuous for ordered dates or numbers"
    )
    sort_x_by: SortBy = Field(
        "axis_x", description="axis_x: sort by X; axis_y: sort by the Y value"
    )
    sort_x_direction: SortDirection = Field("asc", description="Sort direction")
    limit: int | None = Field(
        None,
        ge=XAxis.limit.min_value,
        le=XAxis.limit.max_value,
        description="Number of values shown after the sort "
        f"({XAxis.limit.min_value} to {XAxis.limit.max_value})",
    )


class SeriesInput(BaseModel):
    column_y: str
    aggregate_y: Aggregate | None = None


class YAxisInput(BaseModel):
    label: str | None = Field(None, description="Label of the Y axis")
    unit: str | None = Field(None, description="Unit of the values")
    unit_position: UnitPosition | None = Field(None, description="prefix or suffix")
    min: float | None = Field(None, description="Lower bound of the Y axis")
    max: float | None = Field(None, description="Upper bound of the Y axis")


class CreateChartInput(BaseModel):
    title: StrippedText = Field(description="Title of the chart, not empty")
    description: StrippedText = Field(description="Description of the chart, not empty")
    type: ChartType
    x_axis: XAxisInput
    series: list[SeriesInput] = Field(min_length=1, max_length=4)
    filters: GenericFilter | None = None
    y_axis: YAxisInput | None = None


class UpdateChartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: StrippedText | None = None
    description: StrippedText | None = None
    type: ChartType | None = None
    y_axis: YAxisInput | None = None


def aggregate_error(column: str, aggregate: Aggregate, column_type: str | None) -> str | None:
    """Refusal of an aggregate other than count on a column the profile does not type as numeric."""
    if aggregate == "count" or column_type is None or column_type in NUMERIC_TYPES:
        return None
    return f"The {aggregate} aggregate needs a numeric column: {column} is of type {column_type}."


def query_aggregate_error(column: str, aggregate: Aggregate, column_type: str | None) -> str | None:
    """Like `aggregate_error`, but min and max order any type (e.g. the latest date)."""
    if aggregate in ("min", "max"):
        return None
    return aggregate_error(column, aggregate, column_type)


def unknown_column_errors(names: Iterable[str | None], known: dict[str, str]) -> list[str]:
    """One error per distinct unknown column, in order; empty names are skipped."""
    unknown = dict.fromkeys(name for name in names if name and name not in known)
    return [f"Unknown column: {name}." for name in unknown]


def validate_create(config: CreateChartInput, columns: dict[str, str]) -> list[str]:
    errors = unknown_column_errors(
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
            errors.append(f"The {series.column_y} series must be numeric or aggregated by count.")
    errors.extend(filter_errors(config.filters))
    return errors


class SeriesOutput(BaseModel):
    """A series of the chart model, as cdata sends it to the visualizations API."""

    type: ChartType
    column_y: str
    aggregate_y: Aggregate | None
    resource_id: str
    column_x_name_override: str | None = None
    # The filter tree as the chart model stores it, with its `type` discriminators.
    filters: dict[str, Any] | None


class ChartOutput(BaseModel):
    """The chart handed to cdata, in the shape of the visualizations API."""

    title: str
    description: str
    x_axis: XAxisInput
    y_axis: YAxisInput
    series: list[SeriesOutput]


def to_chart_output(config: CreateChartInput, resource_id: str) -> ChartOutput:
    """Chart of the frontend model; a count series has the X column as `column_y`.

    The chart form reads a series as a count when `column_y` is `column_x`. Every
    count series is then the same: only the first one is kept, in order.
    """
    filters = config.filters.model_dump(by_alias=True) if config.filters else None
    first_count = next((s for s in config.series if s.aggregate_y == "count"), None)
    series = [s for s in config.series if s.aggregate_y != "count" or s is first_count]
    return ChartOutput(
        title=config.title,
        description=config.description,
        x_axis=config.x_axis,
        y_axis=config.y_axis or YAxisInput(),
        series=[
            SeriesOutput(
                type=config.type,
                column_y=config.x_axis.column_x if s.aggregate_y == "count" else s.column_y,
                aggregate_y=s.aggregate_y,
                resource_id=resource_id,
                filters=copy.deepcopy(filters),
            )
            for s in series
        ],
    )


def to_update_output(patch: UpdateChartInput) -> dict:
    """Provided fields only; top-level nulls mean "leave unchanged" and are dropped.

    Inside `y_axis`, an explicit null is kept: it clears that field.
    """
    out = {k: v for k, v in patch.model_dump(exclude_unset=True).items() if v is not None}
    if "y_axis" in out and not out["y_axis"]:
        del out["y_axis"]
    return out
