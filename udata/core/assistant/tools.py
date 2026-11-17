"""Tools attached to the AI assistant agent.

`create_chart` and `update_chart` return dicts (validated chart or patch, or
a list of errors); the other tools return a text. Outputs feed back
into the LLM as tool results, and error cases must be explained, never
raised — an exception escaping a tool kills the whole agent run.
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Annotated, Literal

from mongoengine.errors import DoesNotExist, ValidationError
from pydantic import Field
from pydantic_ai import Agent, RunContext

from udata.core.assistant.charts import (
    CreateChartInput,
    UpdateChartInput,
    profile_columns,
    query_aggregate_error,
    to_chart_output,
    to_update_output,
    unknown_column_errors,
    validate_create,
    validate_update,
)
from udata.core.assistant.data_query import (
    MAX_QUERIES_PER_QUESTION,
    PAGE_SIZE,
    Aggregate,
    GenericFilter,
    build_data_query,
    filter_columns,
    filter_errors,
    with_page,
)
from udata.core.assistant.tabular import (
    TabularClient,
    TabularError,
    TabularRequestRefused,
    TabularResourceUnavailable,
    has_more_rows,
)
from udata.core.dataset.models import Dataset, Resource, get_dataset_by_resource_id
from udata.mongo.queryset import paginate_embedded_list
from udata.utils import normalize_uuid

log = logging.getLogger(__name__)

# Per-turn budgets. Exhausted tool budgets return a refusal the model can
# explain; MODEL_REQUEST_LIMIT (passed as pydantic-ai usage limits) is the
# hard stop for a model that keeps calling tools after a refusal. The query_data
# budget, MAX_QUERIES_PER_QUESTION, lives in data_query next to PAGE_SIZE.
MAX_STEPS = 5
# Resources listed in a dataset's metadata, so a huge dataset cannot flood the context.
MAX_SERIALIZED_RESOURCES = 20
# One request per tool round, plus the refused round and the final answer.
MODEL_REQUEST_LIMIT = MAX_STEPS + 2


@dataclass
class AssistantDeps:
    """Per-turn state shared with the assistant agent.

    Tool calls run in a pydantic-ai worker thread that inherits the request
    context (contextvars), so permission checks use the requesting user's
    identity exactly like the rest of the API.
    """

    tabular: TabularClient
    resource_id: str | None = None
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


def _dataset_for_current_user(dataset_id: str) -> Dataset | None:
    """Fetch a dataset the requesting user is allowed to read, else None.

    Private and deleted datasets are only exposed to their owner, their
    organization or an admin — the same OwnableReadPermission rule as the
    dataset API. Archived ones stay readable: they are only left out of search.
    """
    try:
        dataset = Dataset.objects.exclude("resources").get(id=dataset_id)
    except (DoesNotExist, ValidationError):
        return None
    if dataset.permissions["read"].can():
        return dataset
    return None


def _dataset_for_resource(resource_id: str) -> Dataset | None:
    """Owner dataset of a resource, readable by the requesting user, else None.

    The id is normalized like the endpoint does: the model may write it in uppercase or
    without dashes, ids are stored in their canonical form.
    """
    if (normalized := normalize_uuid(resource_id)) is None:
        return None
    dataset = get_dataset_by_resource_id(normalized, exclude_resources=True)
    if dataset is not None and dataset.permissions["read"].can():
        return dataset
    return None


def render_profile(profile: dict) -> str:
    """Render the columns and line count of an api-tabular profile, whatever its shape."""
    columns = profile_columns(profile)
    lines = ["Columns:", *(f"- {name} ({kind})" for name, kind in columns.items())]
    if not columns:
        lines = ["No column information available."]
    details = profile.get("profile") if isinstance(profile, dict) else None
    total_lines = details.get("total_lines") if isinstance(details, dict) else None
    if isinstance(total_lines, int):
        lines.append(f"Line count: {total_lines}")
    return "\n".join(lines)


# Bounds on what a query result puts in the model's context: the row cap does not
# bound it, a resource can have hundreds of columns and cells of any length.
MAX_CELL_CHARS = 200
MAX_RESULT_CHARS = 10_000


def _cell(value) -> str:
    """A table cell on one line, without the column separator, cut past MAX_CELL_CHARS."""
    text = " ".join(str(value).split()).replace("|", "/")
    return text if len(text) <= MAX_CELL_CHARS else text[:MAX_CELL_CHARS] + "…"


def _render_result(result: dict, *, aggregated: bool = False) -> str:
    """Render the `data` rows of an api-tabular response as a pipe-separated table.

    A query without aggregate has an exact `meta.total`, which tells whether rows are cut.
    An aggregated one has none: its total is not given. Whole rows past MAX_RESULT_CHARS
    are left out, with a note.
    """
    rows = result.get("data") if isinstance(result, dict) else None
    rows = [row for row in rows or [] if isinstance(row, dict)]
    if not rows:
        return "Query run successfully, no row returned."
    meta = result.get("meta")
    total = meta.get("total") if isinstance(meta, dict) and not aggregated else None
    if not isinstance(total, int):
        total = None
    of_total = f" ({total} rows in total)" if total is not None else ""
    columns = list(rows[0])
    lines = [" | ".join(_cell(column) for column in columns)]
    size = len(lines[0])
    if size > MAX_RESULT_CHARS:
        # Too many columns for even the header: nothing useful fits.
        return (
            f"Result not shown: its {len(columns)} columns exceed the allowed "
            f"size{of_total}. Run it again with `columns` to keep only a few of them."
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
            f"Result cut to {shown} rows for its size{of_total}: "
            "select fewer columns or aggregate to see the rest."
        )
    elif total is not None and total > shown:
        lines.append(f"Truncated result: {total} rows in total, first {PAGE_SIZE} rows shown.")
    return "\n".join(lines)


NO_ACTIVE_RESOURCE = "No active resource: open a resource in the data studio."
RESOURCE_NOT_FOUND = "Resource not found: no visible resource matches this identifier."
TABULAR_UNAVAILABLE = "The tabular service is unavailable."
RESOURCE_NOT_IN_TABULAR = (
    "Resource not available in the tabular service: its data cannot be queried."
)


def _tabular_error_message(error: TabularError) -> str:
    """Message for the model; the text of a TabularError is only logged."""
    if isinstance(error, TabularRequestRefused):
        return f"Query refused by the tabular service: {error.detail}."
    if isinstance(error, TabularResourceUnavailable):
        return RESOURCE_NOT_IN_TABULAR
    return TABULAR_UNAVAILABLE


def _active_columns(ctx: RunContext[AssistantDeps]) -> tuple[str, dict[str, str]]:
    """Active resource id and its profile columns, or raise `_ToolRefusal`."""
    resource_id = ctx.deps.resource_id
    if not resource_id:
        raise _ToolRefusal(NO_ACTIVE_RESOURCE)
    if _dataset_for_resource(resource_id) is None:
        raise _ToolRefusal(RESOURCE_NOT_FOUND)
    try:
        profile = ctx.deps.tabular.get_profile(resource_id)
    except TabularError as error:
        raise _ToolRefusal(_tabular_error_message(error)) from error
    return resource_id, profile_columns(profile)


class _ToolRefusal(Exception):
    """Internal: a refusal message to hand back to the model, never escapes a tool."""


def _chart_has_more_groups(
    tabular: TabularClient, resource_id: str, config: CreateChartInput
) -> bool | None:
    """Whether the viewer truncates a series to its first PAGE_SIZE rows, None if unknown.

    Each series is read like the viewer reads it, so a query api-tabular refuses
    raises `TabularRequestRefused`. Raw series share the chart filters, hence
    their row count: they are read once, first, as the most likely to overflow.
    An unavailable service leaves the count unknown: the chart is valid against
    the profile, and the viewer reports the outage itself.
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
                aggregate=(column_y, series.aggregate_y) if aggregated else None,
                filters=config.filters,
                sort=(x, "asc"),
            )
            key = query if aggregated else None
            if key in read:
                continue
            read.add(key)
            first_page = tabular.get_data(resource_id, with_page(query))
            more_groups = more_groups or has_more_rows(first_page)
    except TabularRequestRefused:
        raise
    except TabularError:
        log.warning("Could not check the group count of a chart", exc_info=True)
        return None
    return more_groups


def serialize_dataset_metadata(dataset: Dataset) -> str:
    """JSON metadata of a dataset loaded without its resources, listing the first ones only.

    Shared by the tool and the chat endpoint.
    """
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
value). Returns at most {PAGE_SIZE} rows."""

CREATE_CHART_DESCRIPTION = f"""\
Create a chart on the active resource, replacing the structure of the current chart.

Only call it after a check with `query_data`. Types: line or histogram,
1 to 4 series. Returns the validated chart or the list of errors to fix.
`more_groups` is true when a series has more than {PAGE_SIZE} points (groups,
or rows without aggregate): the chart only shows the first {PAGE_SIZE}, so tell
the user and suggest a filter or an aggregate. null: the check was not possible."""


def register_tools(agent: Agent) -> None:
    """Attach the assistant tools to a pydantic-ai agent."""

    @agent.tool
    def get_dataset_metadata(ctx: RunContext[AssistantDeps], dataset_id: str) -> str:
        """Get the metadata of a dataset: title, license, organization and resources."""
        if refusal := _consume_tool_budget(ctx):
            return refusal
        dataset = _dataset_for_current_user(dataset_id)
        if dataset is None:
            return f'Dataset not found: no dataset matches "{dataset_id}".'
        return serialize_dataset_metadata(dataset)

    @agent.tool
    def inspect_schema(ctx: RunContext[AssistantDeps], resource_id: str) -> str:
        """Inspect the schema of a tabular resource: columns, types and line count."""
        if refusal := _consume_tool_budget(ctx):
            return refusal
        if _dataset_for_resource(resource_id) is None:
            return RESOURCE_NOT_FOUND
        try:
            profile = ctx.deps.tabular.get_profile(resource_id)
        except TabularError as error:
            return _tabular_error_message(error)
        return render_profile(profile)

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
    ) -> str:
        if refusal := _consume_tool_budget(ctx):
            return refusal
        if bool(aggregate_column) != bool(aggregate):
            return "Invalid query: aggregate_column and aggregate go together."
        if groupby and not aggregate:
            return "Invalid query: groupby needs an aggregate (aggregate_column and aggregate)."
        if aggregate and columns:
            return "Invalid query: columns cannot be combined with an aggregate; remove columns."
        if aggregate and sort_column and sort_column != groupby:
            return (
                "Invalid query: sorting is only possible on the groupby column; "
                "the service does not sort on an aggregated value. "
                "Sort in the chart with sort_x_by=axis_y."
            )
        try:
            resource_id, known = _active_columns(ctx)
        except _ToolRefusal as refusal:
            return str(refusal)
        used = [groupby, aggregate_column, sort_column, *(columns or []), *filter_columns(filters)]
        if unknown := unknown_column_errors(used, known):
            return "\n".join(unknown)
        refusals = filter_errors(filters)
        if aggregate and (
            error := query_aggregate_error(aggregate_column, aggregate, known[aggregate_column])
        ):
            refusals.append(error)
        if refusals:
            return "\n".join(refusals)
        if refusal := _consume_query_budget(ctx):
            return refusal
        sort = (sort_column, sort_direction) if sort_column else None
        if sort is None and groupby:
            sort = (groupby, "asc")
        query = build_data_query(
            groupby=groupby,
            aggregate=(aggregate_column, aggregate) if aggregate else None,
            filters=filters,
            sort=sort,
            columns=columns,
        )
        try:
            result = ctx.deps.tabular.get_data(resource_id, with_page(query))
        except TabularError as error:
            return _tabular_error_message(error)
        rendered = _render_result(result, aggregated=bool(groupby))
        if groupby and has_more_rows(result):
            rendered += (
                f"\nMore than {PAGE_SIZE} groups: only the first {PAGE_SIZE} "
                "are taken into account."
            )
        return rendered

    @agent.tool(description=CREATE_CHART_DESCRIPTION)
    def create_chart(ctx: RunContext[AssistantDeps], config: CreateChartInput) -> dict:
        if refusal := _consume_tool_budget(ctx):
            return {"status": "error", "errors": [refusal]}
        try:
            resource_id, known = _active_columns(ctx)
        except _ToolRefusal as refusal:
            return {"status": "error", "errors": [str(refusal)]}
        if errors := validate_create(config, known):
            return {"status": "error", "errors": errors}
        try:
            more_groups = _chart_has_more_groups(ctx.deps.tabular, resource_id, config)
        except TabularRequestRefused as refusal:
            return {"status": "error", "errors": [_tabular_error_message(refusal)]}
        return {
            "status": "ok",
            "chart": to_chart_output(config, resource_id),
            "more_groups": more_groups,
        }

    @agent.tool
    def update_chart(ctx: RunContext[AssistantDeps], patch: UpdateChartInput) -> dict:
        """Update the presentation of the current chart: title, description, type, Y axis.

        Never use it to change the columns, aggregates, filters or X axis:
        use `create_chart` for that.
        """
        if refusal := _consume_tool_budget(ctx):
            return {"status": "error", "errors": [refusal]}
        if errors := validate_update(patch):
            return {"status": "error", "errors": errors}
        return {"status": "ok", "patch": to_update_output(patch)}

    @agent.tool
    def request_clarification(
        ctx: RunContext[AssistantDeps],
        question: str,
        choices: Annotated[list[str], Field(min_length=2, max_length=4)],
    ) -> str:
        """Ask the user for a clarification, offering a list of numbered choices."""
        if refusal := _consume_tool_budget(ctx):
            return refusal
        lines = [question, ""]
        for index, choice in enumerate(choices, start=1):
            lines.append(f"{index}. {choice}")
        return "\n".join(lines)
