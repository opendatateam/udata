"""Tools attached to the AI assistant agent.

Every tool returns a pydantic model: its result, or a `ToolError` listing what to
fix. The model reads them as JSON tool results, and cdata reads the same fields to
build its tool trace. Error cases must be explained, never raised: an exception
escaping a tool kills the whole agent run.
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from udata.core.assistant.charts import (
    ChartOutput,
    CreateChartInput,
    UpdateChartInput,
    query_aggregate_error,
    to_chart_output,
    to_update_output,
    unknown_column_errors,
    validate_create,
)
from udata.core.assistant.data_query import (
    MAX_QUERIES_PER_QUESTION,
    PAGE_SIZE,
    Aggregate,
    Aggregation,
    GenericFilter,
    Sort,
    build_data_query,
    filter_columns,
    filter_errors,
    with_page,
)
from udata.core.assistant.tabular import (
    TabularClient,
    TabularError,
    TabularPage,
    TabularProfile,
    TabularRequestRefused,
    TabularUnexpectedAnswer,
    has_more_rows,
)
from udata.core.dataset.models import Dataset, Resource, get_dataset_and_resource_by_id
from udata.mongo.queryset import paginate_embedded_list

log = logging.getLogger(__name__)

# Tool calls per turn: past it, tools refuse and the model can say why.
MAX_STEPS = 5
# Resources listed in a dataset's metadata, so a huge dataset cannot flood the context.
MAX_SERIALIZED_RESOURCES = 20
# Stops a model that keeps calling tools after the refusal: one request per tool
# round, plus the refused round and the final answer.
MODEL_REQUEST_LIMIT = MAX_STEPS + 2


@dataclass
class AssistantDeps:
    """Per-turn state shared with the assistant agent.

    `resource_id` is the active resource, set only when the requesting user can read
    it (see `load_active_resource`), and `columns` its profile columns, None while
    the profile could not be fetched, and `profile_error` a failure that would repeat.
    """

    tabular: TabularClient
    resource_id: UUID | None = None
    columns: dict[str, str] | None = None
    profile_error: TabularError | None = None
    tool_count: int = 0
    query_count: int = 0
    # Parallel tool calls run in separate threads: budgets are checked and spent atomically.
    budget_lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)


def _consume_tool_budget(ctx: RunContext[AssistantDeps]) -> str | None:
    """Enforce MAX_STEPS as a per-turn tool-call cap.

    Returns a refusal message once the budget is exhausted, None
    otherwise, so the model can still explain the limit in its answer.
    """
    with ctx.deps.budget_lock:
        if ctx.deps.tool_count >= MAX_STEPS:
            return f"Action refused: the limit of {MAX_STEPS} tool calls per turn is reached."
        ctx.deps.tool_count += 1
    return None


def _consume_query_budget(ctx: RunContext[AssistantDeps]) -> str | None:
    """Enforce MAX_QUERIES_PER_QUESTION, returning a refusal once it is exhausted."""
    with ctx.deps.budget_lock:
        if ctx.deps.query_count >= MAX_QUERIES_PER_QUESTION:
            return (
                f"Query refused: the limit of {MAX_QUERIES_PER_QUESTION} "
                "queries per question is reached."
            )
        ctx.deps.query_count += 1
    return None


@dataclass
class ActiveResource:
    dataset: Dataset
    resource: Resource
    profile: TabularProfile | None
    profile_error: TabularError | None = None


def _repeats(error: TabularError) -> bool:
    """Whether fetching again would fail the same way: api-tabular answered, not an outage."""
    if isinstance(error, TabularRequestRefused):
        return error.status < 500
    return isinstance(error, TabularUnexpectedAnswer)


def load_active_resource(resource_id: str, tabular: TabularClient) -> ActiveResource | None:
    """The resource, its dataset and its profile, None unless the user can read the dataset.

    A failed profile fetch leaves `profile` None; the tools fetch it again unless
    `profile_error` says it would fail the same way.
    """
    dataset, resource = get_dataset_and_resource_by_id(resource_id)
    if dataset is None or resource is None or not dataset.permissions["read"].can():
        return None
    try:
        return ActiveResource(dataset, resource, tabular.get_profile(resource.id))
    except TabularError as error:
        log.info("Assistant: profile fetch failed for %s", resource_id)
        return ActiveResource(dataset, resource, None, error if _repeats(error) else None)


def render_profile(profile: TabularProfile) -> str:
    """Render the columns and line count of an api-tabular profile."""
    columns = profile.columns()
    lines = ["Columns:", *(f"- {name} ({kind})" for name, kind in columns.items())]
    if not columns:
        lines = ["No column information available."]
    if profile.profile.total_lines is not None:
        lines.append(f"Line count: {profile.profile.total_lines}")
    return "\n".join(lines)


# Bounds on a query result: even 50 rows can be huge with many columns or long cells.
MAX_CELL_CHARS = 200
MAX_RESULT_CHARS = 10_000


def _cell(value) -> str:
    """A table cell on one line, without the column separator, cut past MAX_CELL_CHARS."""
    text = " ".join(str(value).split()).replace("|", "/")
    return text if len(text) <= MAX_CELL_CHARS else text[:MAX_CELL_CHARS] + "…"


class ToolError(BaseModel):
    status: Literal["error"] = "error"
    errors: list[str]


class QueryOutput(BaseModel):
    """A `query_data` result: the table the model reads, and its counts for cdata."""

    status: Literal["ok"] = "ok"
    table: str
    # Rows in `table`.
    rows: int
    # Rows the query matches, known only without an aggregate.
    total: int | None = None
    # More than PAGE_SIZE groups: only the first ones are in `table`.
    more_groups: bool = False


class ChartToolOutput(BaseModel):
    status: Literal["ok"] = "ok"
    chart: ChartOutput
    more_groups: bool | None


class UpdateToolOutput(BaseModel):
    status: Literal["ok"] = "ok"
    # A dict, not a model: fields left out must not come out as nulls.
    patch: dict[str, Any]


def _refused(*errors: str) -> ToolError:
    return ToolError(errors=list(errors))


def _render_result(page: TabularPage) -> QueryOutput | ToolError:
    """The rows of an api-tabular page as a pipe-separated table.

    Whole rows past MAX_RESULT_CHARS are left out, with a note.
    """
    rows = page.data
    total = page.meta.total
    if not rows:
        return QueryOutput(table="", rows=0, total=total)
    columns = list(rows[0])
    lines = [" | ".join(_cell(column) for column in columns)]
    size = len(lines[0])
    if size > MAX_RESULT_CHARS:
        # Too many columns for even the header: nothing useful fits.
        return _refused(
            f"Result not shown: its {len(columns)} columns exceed the allowed size. "
            "Run it again with `columns` to keep only a few of them."
        )
    shown = 0
    for row in rows[:PAGE_SIZE]:
        line = " | ".join(_cell(row.get(column)) for column in columns)
        size += len(line) + 1
        if size > MAX_RESULT_CHARS:
            break
        lines.append(line)
        shown += 1
    if shown < min(len(rows), PAGE_SIZE):
        lines.append(
            f"Result cut to {shown} rows for its size: "
            "select fewer columns or aggregate to see the rest."
        )
    return QueryOutput(table="\n".join(lines), rows=shown, total=total)


NO_ACTIVE_RESOURCE = "No active resource: open a resource in the data studio."
TABULAR_UNAVAILABLE = "The tabular service is unavailable."
TABULAR_UNREADABLE = "The tabular service answered in a form the assistant cannot read."


def _tabular_error_message(error: TabularError) -> str:
    """Message for the model: api-tabular's own answer when it gave one."""
    if isinstance(error, TabularRequestRefused):
        return f"The tabular service answered {error.status}: {error.detail}"
    if isinstance(error, TabularUnexpectedAnswer):
        return TABULAR_UNREADABLE
    return TABULAR_UNAVAILABLE


def _active_columns(ctx: RunContext[AssistantDeps]) -> tuple[UUID, dict[str, str]]:
    """Active resource id and its profile columns, or raise `_ToolRefusal`.

    The columns come from the request's profile fetch; a failed one is tried again,
    unless it would fail the same way, and its result kept for the next tools. Parallel
    tool calls may both fetch it: the profile is the same.
    """
    deps = ctx.deps
    if not deps.resource_id:
        raise _ToolRefusal(NO_ACTIVE_RESOURCE)
    if deps.profile_error:
        raise _ToolRefusal(_tabular_error_message(deps.profile_error))
    if deps.columns is None:
        try:
            deps.columns = deps.tabular.get_profile(deps.resource_id).columns()
        except TabularError as error:
            if _repeats(error):
                deps.profile_error = error
            raise _ToolRefusal(_tabular_error_message(error)) from error
    return deps.resource_id, deps.columns


class _ToolRefusal(Exception):
    """Internal: a refusal message to hand back to the model, never escapes a tool."""


def _chart_has_more_groups(
    tabular: TabularClient, resource_id: UUID, config: CreateChartInput
) -> bool | None:
    """Whether the viewer warns that a series is cut to its first PAGE_SIZE rows, None if unknown.

    Each series is read like the viewer reads it, so a query api-tabular refuses
    raises `TabularRequestRefused`. Raw series share the chart filters, hence
    their row count: they are read once, first, as the most likely to overflow.
    An unavailable service leaves the count unknown: the chart is valid against
    the profile, and the viewer reports the outage itself.

    Like the viewer, an X order with a limit within PAGE_SIZE is never cut: the limit
    keeps the first values of the extract, which are the right ones. The series are
    still read, to catch a refused query.
    """
    x = config.x_axis.column_x
    read = set()
    more_groups = False
    try:
        for series in sorted(config.series, key=lambda series: series.aggregate_y is not None):
            aggregated = series.aggregate_y is not None
            # Like the chart output: a count series counts the X column.
            column_y = x if series.aggregate_y == "count" else series.column_y
            query = build_data_query(
                # Like the viewer: grouped with an aggregate, the two raw columns without.
                columns=None if aggregated else [x, column_y],
                groupby=x if aggregated else None,
                aggregate=Aggregation(column_y, series.aggregate_y) if aggregated else None,
                filters=config.filters,
                sort=Sort(x, "asc"),
            )
            key = query if aggregated else None
            if key in read:
                continue
            read.add(key)
            first_page = tabular.get_data(resource_id, with_page(query))
            more_groups = more_groups or has_more_rows(first_page)
    except TabularRequestRefused as refusal:
        if refusal.status < 500:
            raise
        log.warning("Could not check the group count of a chart", exc_info=True)
        return None
    except TabularError:
        log.warning("Could not check the group count of a chart", exc_info=True)
        return None
    limit = config.x_axis.limit
    if config.x_axis.sort_x_by != "axis_y" and limit is not None and limit <= PAGE_SIZE:
        return False
    return more_groups


def serialize_dataset_metadata(dataset: Dataset) -> str:
    """JSON metadata of a dataset loaded without its resources, listing the first ones only."""
    resources, total = paginate_embedded_list(
        Dataset, dataset.id, "resources", Resource, page=1, page_size=MAX_SERIALIZED_RESOURCES
    )
    payload = {
        "id": str(dataset.id),
        "title": dataset.title,
        "license": dataset.license.title if dataset.license else None,
        "organization": dataset.organization.name if dataset.organization else None,
        "resources": [
            {"id": str(resource.id), "title": resource.title, "format": resource.format}
            for resource in resources
        ],
    }
    if total > len(resources):
        payload["more_resources"] = f"… and {total - len(resources)} more"
    return json.dumps(payload, ensure_ascii=False, indent=2)


# Tool descriptions given explicitly, as f-strings, to quote the page size.
QUERY_DATA_DESCRIPTION = f"""\
Query the active resource (read only) to check the data before a chart.

An aggregate without `groupby` is allowed: it gives an overall total.
To group, set `groupby`, `aggregate_column` and `aggregate`
(avg, sum, count, min, max). Without an explicit sort, a grouping is sorted
on the groupby column. With an aggregate, do not pass `columns` and only
sort on the `groupby` column (the service does not sort on an aggregated
value). Returns at most {PAGE_SIZE} rows in `table`, with `rows` the number
shown, `total` the number of matching rows when known (without aggregate),
and `more_groups` true when there are more than {PAGE_SIZE} groups."""

CREATE_CHART_DESCRIPTION = f"""\
Create a chart on the active resource, replacing the structure of the current chart.

Only call it after a check with `query_data`. Types: line or histogram,
1 to 4 series. Returns the validated chart or the list of errors to fix.
`more_groups` is true when a series has more than {PAGE_SIZE} points (groups,
or rows without aggregate) and the chart only shows the first {PAGE_SIZE}: tell
the user and suggest a filter or an aggregate. It is false with an X sort and a
limit up to {PAGE_SIZE}, which the chart shows in full. null: the check was not
possible."""


def register_tools(agent: Agent) -> None:
    """Attach the assistant tools to a pydantic-ai agent."""

    @agent.tool(description=QUERY_DATA_DESCRIPTION)
    def query_data(
        ctx: RunContext[AssistantDeps],
        groupby: str | None = None,
        aggregate_column: str | None = None,
        aggregate: Aggregate | None = None,
        filters: GenericFilter | None = None,
        sort_column: str | None = None,
        sort_direction: Literal["asc", "desc"] = "asc",
        columns: list[str] | None = None,
    ) -> QueryOutput | ToolError:
        if refusal := _consume_tool_budget(ctx):
            return _refused(refusal)
        if bool(aggregate_column) != bool(aggregate):
            return _refused("Invalid query: aggregate_column and aggregate go together.")
        if groupby and not aggregate:
            return _refused(
                "Invalid query: groupby needs an aggregate (aggregate_column and aggregate)."
            )
        if aggregate and columns:
            return _refused(
                "Invalid query: columns cannot be combined with an aggregate; remove columns."
            )
        if aggregate and sort_column and sort_column != groupby:
            return _refused(
                "Invalid query: sorting is only possible on the groupby column; "
                "the service does not sort on an aggregated value. "
                "Sort in the chart with sort_x_by=axis_y."
            )
        try:
            resource_id, known = _active_columns(ctx)
        except _ToolRefusal as refusal:
            return _refused(str(refusal))
        used = [groupby, aggregate_column, sort_column, *(columns or []), *filter_columns(filters)]
        if unknown := unknown_column_errors(used, known):
            return _refused(*unknown)
        refusals = filter_errors(filters)
        if aggregate and (
            error := query_aggregate_error(aggregate_column, aggregate, known[aggregate_column])
        ):
            refusals.append(error)
        if refusals:
            return _refused(*refusals)
        if refusal := _consume_query_budget(ctx):
            return _refused(refusal)
        sort = Sort(sort_column, sort_direction) if sort_column else None
        if sort is None and groupby:
            sort = Sort(groupby, "asc")
        query = build_data_query(
            groupby=groupby,
            aggregate=Aggregation(aggregate_column, aggregate) if aggregate else None,
            filters=filters,
            sort=sort,
            columns=columns,
        )
        try:
            result = ctx.deps.tabular.get_data(resource_id, with_page(query))
        except TabularError as error:
            return _refused(_tabular_error_message(error))
        output = _render_result(result)
        if isinstance(output, QueryOutput) and groupby:
            output.more_groups = has_more_rows(result)
        return output

    @agent.tool(description=CREATE_CHART_DESCRIPTION)
    def create_chart(
        ctx: RunContext[AssistantDeps], config: CreateChartInput
    ) -> ChartToolOutput | ToolError:
        if refusal := _consume_tool_budget(ctx):
            return _refused(refusal)
        try:
            resource_id, known = _active_columns(ctx)
        except _ToolRefusal as refusal:
            return _refused(str(refusal))
        if errors := validate_create(config, known):
            return _refused(*errors)
        try:
            more_groups = _chart_has_more_groups(ctx.deps.tabular, resource_id, config)
        except TabularRequestRefused as refusal:
            return _refused(_tabular_error_message(refusal))
        return ChartToolOutput(
            chart=to_chart_output(config, str(resource_id)), more_groups=more_groups
        )

    @agent.tool
    def update_chart(
        ctx: RunContext[AssistantDeps], patch: UpdateChartInput
    ) -> UpdateToolOutput | ToolError:
        """Update the presentation of the current chart: title, description, type, Y axis.

        Never use it to change the columns, aggregates, filters or X axis:
        use `create_chart` for that.
        """
        if refusal := _consume_tool_budget(ctx):
            return _refused(refusal)
        if not (changes := to_update_output(patch)):
            return _refused("At least one change is required.")
        return UpdateToolOutput(patch=changes)
