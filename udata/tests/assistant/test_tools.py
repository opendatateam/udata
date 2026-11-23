"""Tools attached to the AI assistant agent: tests.

Permissions are checked once per request by `load_active_resource`: the tools only
see the active resource the requesting user can read, through `AssistantDeps`.
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from udata.auth import login_user
from udata.core.assistant.charts import CreateChartInput, UpdateChartInput
from udata.core.assistant.data_query import MAX_QUERIES_PER_QUESTION, PAGE_SIZE, Filter
from udata.core.assistant.tabular import TabularClient, TabularPage, TabularProfile
from udata.core.assistant.tools import (
    MAX_CELL_CHARS,
    MAX_RESULT_CHARS,
    MAX_SERIALIZED_RESOURCES,
    MAX_STEPS,
    NO_ACTIVE_RESOURCE,
    TABULAR_UNREADABLE,
    AssistantDeps,
    QueryOutput,
    ToolError,
    UpdateToolOutput,
    _render_result,
    load_active_resource,
    register_tools,
    render_profile,
    serialize_dataset_metadata,
)
from udata.core.dataset.factories import DatasetFactory, LicenseFactory, ResourceFactory
from udata.core.dataset.models import Dataset
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.tests.api import PytestOnlyDBTestCase


class SlowCountersDeps(AssistantDeps):
    """Deps whose budget counters yield the thread on every read, widening any
    gap between a budget check and its increment."""

    @property
    def tool_count(self):
        time.sleep(0.005)
        return self._tool_count

    @tool_count.setter
    def tool_count(self, value):
        self._tool_count = value

    @property
    def query_count(self):
        # Longer than the tool budget section, which already serializes the calls.
        time.sleep(0.05)
        return self._query_count

    @query_count.setter
    def query_count(self, value):
        self._query_count = value


COLUMNS = {"dep": "string", "n_cum_dose1": "int", "label": "string"}
# More departments than a page holds, each with its doses and a label.
MANY_DEPS = [{"dep": f"{i:02}", "n_cum_dose1": i, "label": "x"} for i in range(PAGE_SIZE + 1)]


class AssistantToolsTest(PytestOnlyDBTestCase):
    @pytest.fixture(autouse=True)
    def _tabular(self, tabular):
        self.tabular = tabular

    def setup_method(self, method):
        self.agent = Agent(model=TestModel(), deps_type=AssistantDeps)
        register_tools(self.agent)
        self.tools = self.agent._function_toolset.tools

    @contextmanager
    def request_as(self, user=None):
        """Request context whose flask-principal identity is ``user`` (anonymous if None)."""
        with self.app.test_request_context():
            self.app.preprocess_request()
            if user is not None:
                login_user(user)
            yield

    def call(self, name, deps, **kwargs):
        ctx = SimpleNamespace(deps=deps)
        return self.tools[name].function(ctx, **kwargs)

    def make_deps(self, **kwargs):
        return AssistantDeps(tabular=TabularClient(), **kwargs)

    def owned_resource(self, **dataset_kwargs):
        """A resource with a dataset; public unless ``dataset_kwargs`` say otherwise."""
        resource = ResourceFactory()
        dataset_kwargs.setdefault("title", "Données de test")
        DatasetFactory(resources=[resource], **dataset_kwargs)
        return resource

    def active(self, columns=COLUMNS, rows=None):
        """Deps on an active resource of api-tabular whose profile columns are already known."""
        rid = uuid4()
        self.tabular.add_resource(rid, columns, rows)
        return self.make_deps(resource_id=rid, columns=dict(columns)), rid

    def active_without_profile(self):
        """Deps on an active resource of api-tabular whose profile is still to fetch."""
        deps, _rid = self.active()
        deps.columns = None
        return deps

    def chart_config(self, **kwargs):
        config = {
            "title": "Doses",
            "description": "Doses par département",
            "type": "line",
            "x_axis": {"column_x": "dep", "type": "discrete"},
            "series": [{"column_y": "n_cum_dose1", "aggregate_y": "max"}],
        }
        config.update(kwargs)
        return CreateChartInput(**config)

    # Dataset metadata and profile given to the model with the active resource.

    def test_serialize_dataset_metadata_serializes_dataset(self):
        license = LicenseFactory(title="Licence Ouverte")
        organization = OrganizationFactory(name="Ma collectivité")
        resources = ResourceFactory.build_batch(2)
        dataset = DatasetFactory(
            title="Données de test",
            license=license,
            organization=organization,
            resources=resources,
        )
        payload = json.loads(serialize_dataset_metadata(dataset))
        assert payload["id"] == str(dataset.id)
        assert payload["title"] == "Données de test"
        assert payload["license"] == "Licence Ouverte"
        assert payload["organization"] == "Ma collectivité"
        assert len(payload["resources"]) == len(dataset.resources)
        first = dataset.resources[0]
        assert payload["resources"][0] == {
            "id": str(first.id),
            "title": first.title,
            "format": first.format,
        }

    def test_serialize_dataset_metadata_caps_the_listed_resources(self):
        resources = ResourceFactory.build_batch(MAX_SERIALIZED_RESOURCES + 3)
        dataset = DatasetFactory(resources=resources)
        payload = json.loads(serialize_dataset_metadata(dataset))
        listed = [resource["id"] for resource in payload["resources"]]
        assert listed == [str(r.id) for r in resources[:MAX_SERIALIZED_RESOURCES]]
        assert payload["more_resources"] == "… and 3 more"

    def test_serialize_dataset_metadata_of_a_dataset_stored_without_resources(self):
        dataset = DatasetFactory(title="Sans ressources")
        Dataset._get_collection().update_one({"_id": dataset.id}, {"$unset": {"resources": ""}})
        payload = json.loads(serialize_dataset_metadata(dataset))
        assert payload["title"] == "Sans ressources"
        assert payload["resources"] == []
        assert "more_resources" not in payload

    def test_render_profile_lists_columns_types_and_rows(self):
        profile = TabularProfile.model_validate(
            {
                "profile": {
                    "header": ["col_a", "col_b"],
                    "columns": {
                        "col_b": {"python_type": "string"},
                        "col_a": {"python_type": "int"},
                    },
                    "total_lines": 42,
                }
            }
        )
        result = render_profile(profile)
        assert "- col_a (int)\n- col_b (string)" in result
        assert "Line count: 42" in result

    def test_render_profile_without_columns_says_so(self):
        profile = TabularProfile.model_validate({"profile": {"columns": {}}})
        assert render_profile(profile) == "No column information available."

    # Active resource: permission and profile.

    def test_load_active_resource_hides_resource_of_private_dataset_from_anonymous(self):
        resource = self.owned_resource(private=True)
        with self.request_as():
            assert load_active_resource(str(resource.id), TabularClient()) is None
        assert self.tabular.profile_requests == []

    def test_load_active_resource_owner_of_private_dataset_is_allowed(self):
        owner = UserFactory()
        resource = self.owned_resource(private=True, owner=owner)
        self.tabular.add_resource(resource.id, COLUMNS)
        with self.request_as(owner):
            active = load_active_resource(str(resource.id), TabularClient())
        assert active is not None
        assert active.dataset.title == "Données de test"
        assert active.resource.id == resource.id
        assert active.profile.columns() == COLUMNS

    def test_load_active_resource_unknown_resource_returns_none(self):
        with self.request_as():
            assert load_active_resource(str(uuid4()), TabularClient()) is None
        assert self.tabular.profile_requests == []

    def test_load_active_resource_keeps_the_resource_when_the_profile_fetch_fails(self):
        resource = self.owned_resource()
        self.tabular.unreachable()
        with self.request_as():
            active = load_active_resource(str(resource.id), TabularClient())
        assert active is not None
        assert active.resource.id == resource.id
        assert active.profile is None
        assert active.profile_error is None

    def test_tools_require_an_active_resource(self):
        deps = self.make_deps()
        assert self.call("query_data", deps) == ToolError(errors=[NO_ACTIVE_RESOURCE])
        result = self.call("create_chart", deps, config=self.chart_config())
        assert result == ToolError(errors=[NO_ACTIVE_RESOURCE])
        assert self.tabular.profile_requests == []

    def test_known_columns_are_used_without_fetching_the_profile(self):
        deps, _rid = self.active()
        assert self.call("query_data", deps, columns=["dep"]).status == "ok"
        assert self.tabular.profile_requests == []

    def test_the_profile_is_fetched_once_and_kept_for_the_next_tools(self):
        deps = self.active_without_profile()
        assert self.call("query_data", deps, columns=["dep"]).status == "ok"
        assert self.call("create_chart", deps, config=self.chart_config()).status == "ok"
        assert self.tabular.profile_requests == [str(deps.resource_id)]
        assert deps.columns == COLUMNS

    def test_a_failed_profile_fetch_is_tried_again_by_the_next_tool(self):
        deps = self.active_without_profile()
        self.tabular.unreachable()
        result = self.call("query_data", deps)
        assert result == ToolError(errors=["The tabular service is unavailable."])
        assert deps.columns is None
        self.tabular.recovers()
        assert self.call("query_data", deps).status == "ok"
        assert len(self.tabular.profile_requests) == 2
        assert deps.columns == COLUMNS

    def test_an_unreadable_profile_is_not_fetched_again(self):
        deps = self.active_without_profile()
        self.tabular.answers_unreadable()
        assert self.call("query_data", deps) == ToolError(errors=[TABULAR_UNREADABLE])
        result = self.call("create_chart", deps, config=self.chart_config())
        assert result == ToolError(errors=[TABULAR_UNREADABLE])
        assert len(self.tabular.profile_requests) == 1

    def test_a_profile_refused_by_the_service_is_relayed_without_being_fetched_again(self):
        # A resource api-tabular does not know.
        deps = self.make_deps(resource_id=uuid4())
        for _ in range(2):
            result = self.call("query_data", deps)
            assert result.errors == ["The tabular service answered 404: 404: Not Found"]
        assert len(self.tabular.profile_requests) == 1

    def test_load_active_resource_keeps_a_profile_failure_that_would_repeat(self):
        resource = self.owned_resource()
        with self.request_as():
            active = load_active_resource(str(resource.id), TabularClient())
        assert active.profile is None
        assert active.profile_error.status == 404

    # Budgets.

    def test_tool_budget_caps_the_calls_of_every_tool(self):
        """MAX_STEPS caps the tool calls of a run, whatever the tools called."""
        deps, _ = self.active()
        calls = [
            ("query_data", {}),
            ("update_chart", {"patch": UpdateChartInput(title="Neuf")}),
        ]
        for index in range(MAX_STEPS):
            name, kwargs = calls[index % len(calls)]
            assert self.call(name, deps, **kwargs).status == "ok"
        result = self.call("create_chart", deps, config=self.chart_config())
        assert result == ToolError(
            errors=[f"Action refused: the limit of {MAX_STEPS} tool calls per turn is reached."]
        )
        assert deps.tool_count == MAX_STEPS

    def _race(self, name, deps, calls, **kwargs):
        """Run ``calls`` concurrent calls of a tool, all released at once."""
        barrier = threading.Barrier(calls)

        def call():
            barrier.wait()
            return self.call(name, deps, **kwargs)

        with ThreadPoolExecutor(max_workers=calls) as pool:
            return list(pool.map(lambda _: call(), range(calls)))

    def test_tool_budget_holds_under_parallel_calls(self):
        deps = SlowCountersDeps(tabular=TabularClient())
        results = self._race(
            "update_chart", deps, 2 * MAX_STEPS, patch=UpdateChartInput(title="Neuf")
        )
        assert sum(result.status == "ok" for result in results) == MAX_STEPS

    def test_query_budget_holds_under_parallel_calls(self):
        _deps, rid = self.active()
        deps = SlowCountersDeps(tabular=TabularClient(), resource_id=rid, columns=dict(COLUMNS))
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("udata.core.assistant.tools.MAX_STEPS", 100)
            results = self._race("query_data", deps, 2 * MAX_QUERIES_PER_QUESTION)
        assert sum(result.status == "ok" for result in results) == MAX_QUERIES_PER_QUESTION

    def test_query_data_caps_queries_per_question(self):
        deps, _ = self.active()
        for _ in range(MAX_QUERIES_PER_QUESTION):
            assert self.call("query_data", deps).status == "ok"
        result = self.call("query_data", deps)
        assert result.errors == ["Query refused: the limit of 3 queries per question is reached."]

    # query_data.

    MAX_BY_DEP = "dep__groupby&n_cum_dose1__max&dep__sort=asc&page=1&page_size=50"

    def test_query_data_groups_and_sorts_on_x(self):
        deps, _ = self.active(rows=[{"dep": "01", "n_cum_dose1": 3, "label": "x"}])
        result = self.call(
            "query_data", deps, groupby="dep", aggregate_column="n_cum_dose1", aggregate="max"
        )
        assert self.tabular.queries == [self.MAX_BY_DEP]
        assert result == QueryOutput(table="dep | n_cum_dose1__max\n01 | 3", rows=1)

    def test_query_data_reports_more_than_50_groups(self):
        deps, _ = self.active(rows=MANY_DEPS)
        result = self.call(
            "query_data", deps, groupby="dep", aggregate_column="n_cum_dose1", aggregate="max"
        )
        assert result.more_groups is True
        assert result.rows == PAGE_SIZE
        assert result.total is None
        assert self.tabular.queries == [self.MAX_BY_DEP]

    def test_query_data_reports_the_total_of_truncated_rows(self):
        deps, _ = self.active(rows=[{"dep": "01"}] * 926)
        result = self.call("query_data", deps, columns=["dep"])
        assert result.total == 926
        assert result.rows == PAGE_SIZE
        assert result.more_groups is False

    def test_query_data_does_not_flag_exactly_50_groups(self):
        deps, _ = self.active(rows=MANY_DEPS[:PAGE_SIZE])
        result = self.call(
            "query_data", deps, groupby="dep", aggregate_column="n_cum_dose1", aggregate="max"
        )
        assert result.more_groups is False
        assert result.rows == PAGE_SIZE

    def test_query_data_allows_a_global_aggregate(self):
        deps, _ = self.active(rows=[{"n_cum_dose1": 2}, {"n_cum_dose1": 3}])
        result = self.call("query_data", deps, aggregate_column="n_cum_dose1", aggregate="sum")
        assert self.tabular.queries == ["n_cum_dose1__sum&page=1&page_size=50"]
        assert result.table == "n_cum_dose1__sum\n5"

    def test_query_data_refuses_an_aggregate_column_without_aggregate(self):
        deps, _ = self.active()
        result = self.call("query_data", deps, aggregate_column="n_cum_dose1")
        assert result.errors == ["Invalid query: aggregate_column and aggregate go together."]
        assert self.tabular.queries == []

    def test_query_data_refuses_groupby_without_aggregate(self):
        deps, _ = self.active()
        result = self.call("query_data", deps, groupby="dep")
        assert result.errors == [
            "Invalid query: groupby needs an aggregate (aggregate_column and aggregate)."
        ]
        assert self.tabular.queries == []

    def test_query_data_refuses_columns_with_an_aggregate(self):
        deps = self.active_without_profile()
        result = self.call(
            "query_data",
            deps,
            groupby="dep",
            aggregate_column="n_cum_dose1",
            aggregate="sum",
            columns=["dep"],
        )
        assert result.errors == [
            "Invalid query: columns cannot be combined with an aggregate; remove columns."
        ]
        assert self.tabular.queries == []
        assert self.tabular.profile_requests == []
        assert deps.tool_count == 1
        assert deps.query_count == 0
        self.call("query_data", deps)
        assert deps.query_count == 1

    def test_query_data_refuses_sorting_on_an_aggregated_column(self):
        deps = self.active_without_profile()
        result = self.call(
            "query_data",
            deps,
            groupby="dep",
            aggregate_column="n_cum_dose1",
            aggregate="sum",
            sort_column="n_cum_dose1",
            sort_direction="desc",
        )
        assert result.status == "error"
        assert "sorting is only possible on the groupby column" in result.errors[0]
        assert "sort_x_by=axis_y" in result.errors[0]
        assert self.tabular.queries == []
        assert self.tabular.profile_requests == []
        assert deps.tool_count == 1
        assert deps.query_count == 0
        ok = self.call(
            "query_data",
            deps,
            groupby="dep",
            aggregate_column="n_cum_dose1",
            aggregate="sum",
            sort_column="dep",
        )
        assert ok.status == "ok"
        assert len(self.tabular.queries) == 1
        assert deps.query_count == 1

    def test_query_data_refuses_a_global_aggregate_with_a_sort(self):
        deps = self.active_without_profile()
        result = self.call(
            "query_data",
            deps,
            aggregate_column="n_cum_dose1",
            aggregate="sum",
            sort_column="dep",
        )
        assert "sorting is only possible on the groupby column" in result.errors[0]
        assert self.tabular.queries == []
        assert self.tabular.profile_requests == []
        assert deps.query_count == 0

    def test_query_data_rejects_an_unknown_column(self):
        deps, _ = self.active()
        result = self.call("query_data", deps, sort_column="foo")
        assert result.errors == ["Unknown column: foo."]
        assert self.tabular.queries == []
        assert deps.query_count == 0

    def test_query_data_relays_the_service_refusal(self):
        deps, _ = self.active()
        self.tabular.fails_with(400, "bad param")
        result = self.call("query_data", deps)
        assert result == ToolError(errors=["The tabular service answered 400: bad param"])

    def test_query_data_tabular_error_is_a_message(self):
        deps, _ = self.active()
        self.tabular.unreachable()
        result = self.call("query_data", deps)
        assert result == ToolError(errors=["The tabular service is unavailable."])

    def test_query_data_refuses_a_filter_without_value_without_using_a_query(self):
        deps, _ = self.active()
        flt = {"column": "dep", "condition": "exact", "value": ""}
        result = self.call("query_data", deps, filters=Filter(**flt))
        assert result.errors == ["The exact filter on dep needs a value."]
        assert self.tabular.queries == []
        assert deps.query_count == 0

    def test_query_data_rejects_an_unknown_filter_column(self):
        deps, _ = self.active()
        flt = {"column": "foo", "condition": "exact", "value": "1"}
        result = self.call("query_data", deps, filters=Filter(**flt))
        assert result.errors == ["Unknown column: foo."]
        assert self.tabular.queries == []

    @pytest.mark.parametrize("aggregate", ["sum", "avg"])
    def test_query_data_refuses_a_numeric_aggregate_on_text_without_using_a_query(self, aggregate):
        deps, _ = self.active()
        result = self.call(
            "query_data", deps, groupby="dep", aggregate_column="label", aggregate=aggregate
        )
        assert result.errors == [
            f"The {aggregate} aggregate needs a numeric column: label is of type string."
        ]
        assert self.tabular.queries == []
        assert deps.query_count == 0

    @pytest.mark.parametrize("aggregate", ["min", "max"])
    def test_query_data_allows_min_max_on_a_text_column(self, aggregate):
        # Exploring, e.g. the latest date of a column api-tabular types as string.
        deps, _ = self.active()
        result = self.call("query_data", deps, aggregate_column="label", aggregate=aggregate)
        assert result.status == "ok"
        assert self.tabular.queries == [f"label__{aggregate}&page=1&page_size=50"]

    def test_query_data_reads_a_column_whose_name_has_a_comma(self):
        deps, _ = self.active(columns={"a,b": "int"}, rows=[{"a,b": 1}])
        assert self.call("query_data", deps, columns=["a,b"]).rows == 1

    def test_query_data_counts_a_text_column(self):
        deps, _ = self.active()
        result = self.call(
            "query_data", deps, groupby="dep", aggregate_column="label", aggregate="count"
        )
        assert result == QueryOutput(table="", rows=0)
        assert self.tabular.queries == [
            "dep__groupby&label__count&dep__sort=asc&page=1&page_size=50"
        ]

    # create_chart.

    AGGREGATED = "dep__groupby&n_cum_dose1__max&dep__sort=asc"
    RAW = "columns=dep,n_cum_dose1&dep__sort=asc"

    def test_create_chart_returns_the_validated_chart(self):
        deps, rid = self.active()
        result = self.call("create_chart", deps, config=self.chart_config())
        assert self.tabular.queries == [f"{self.AGGREGATED}&page=1&page_size=50"]
        assert result.status == "ok"
        chart = result.chart.model_dump()
        assert chart["title"] == "Doses"
        assert chart["series"] == [
            {
                "type": "line",
                "column_y": "n_cum_dose1",
                "aggregate_y": "max",
                "resource_id": str(rid),
                "column_x_name_override": None,
                "filters": None,
            }
        ]
        assert result.more_groups is False

    def test_create_chart_returns_errors_for_an_invalid_config(self):
        deps, _ = self.active()
        config = self.chart_config(x_axis={"column_x": "foo", "type": "discrete"})
        result = self.call("create_chart", deps, config=config)
        assert result == ToolError(errors=["Unknown column: foo."])
        assert self.tabular.queries == []

    def test_create_chart_flags_more_groups_from_the_first_page(self):
        deps, _ = self.active(rows=MANY_DEPS)
        result = self.call("create_chart", deps, config=self.chart_config())
        assert result.more_groups is True
        assert self.tabular.queries == [f"{self.AGGREGATED}&page=1&page_size=50"]

    def test_create_chart_with_an_x_sort_and_a_limit_within_a_page_is_never_cut(self):
        deps, _ = self.active(rows=MANY_DEPS)
        x_axis = {"column_x": "dep", "type": "discrete", "limit": 20}
        result = self.call("create_chart", deps, config=self.chart_config(x_axis=x_axis))
        assert result.status == "ok"
        assert result.more_groups is False
        assert self.tabular.queries == [f"{self.AGGREGATED}&page=1&page_size=50"]

    def test_create_chart_with_a_y_sort_and_a_limit_still_flags_more_groups(self):
        # Sorted on Y, the limit keeps the top values of all the groups, not of the first page.
        deps, _ = self.active(rows=MANY_DEPS)
        x_axis = {"column_x": "dep", "type": "discrete", "sort_x_by": "axis_y", "limit": 20}
        result = self.call("create_chart", deps, config=self.chart_config(x_axis=x_axis))
        assert result.more_groups is True

    def test_create_chart_with_an_x_sort_and_a_limit_still_refuses_a_refused_query(self):
        deps, _ = self.active()
        self.tabular.fails_with(400, "bad param")
        x_axis = {"column_x": "dep", "type": "discrete", "limit": 20}
        result = self.call("create_chart", deps, config=self.chart_config(x_axis=x_axis))
        assert result == ToolError(errors=["The tabular service answered 400: bad param"])

    def test_create_chart_sends_the_filters_with_the_page(self):
        deps, _ = self.active(rows=MANY_DEPS)
        config = self.chart_config(
            filters={"column": "n_cum_dose1", "condition": "less", "value": "14"}
        )
        result = self.call("create_chart", deps, config=config)
        assert result.more_groups is False
        assert self.tabular.queries == [
            f"{self.AGGREGATED}&n_cum_dose1__less=14&page=1&page_size=50"
        ]

    def test_create_chart_reads_one_page_per_distinct_series(self):
        # Raw series share their filters, hence their total: one page covers them all.
        deps, _ = self.active(columns={**COLUMNS, "n2": "int"})
        series = [
            {"column_y": "label", "aggregate_y": "count"},
            {"column_y": "n_cum_dose1"},
            {"column_y": "n2"},
            {"column_y": "n_cum_dose1", "aggregate_y": "max"},
        ]
        result = self.call("create_chart", deps, config=self.chart_config(series=series))
        assert result.more_groups is False
        assert self.tabular.queries == [
            f"{self.RAW}&page=1&page_size=50",
            "dep__groupby&dep__count&dep__sort=asc&page=1&page_size=50",
            f"{self.AGGREGATED}&page=1&page_size=50",
        ]

    def test_create_chart_reads_a_count_on_the_x_column(self):
        # The chart output counts the X column whatever the column_y: one read.
        deps, _ = self.active()
        series = [
            {"column_y": "label", "aggregate_y": "count"},
            {"column_y": "n_cum_dose1", "aggregate_y": "count"},
        ]
        result = self.call("create_chart", deps, config=self.chart_config(series=series))
        assert result.more_groups is False
        assert [s["column_y"] for s in result.chart.model_dump()["series"]] == ["dep"]
        assert self.tabular.queries == ["dep__groupby&dep__count&dep__sort=asc&page=1&page_size=50"]

    def test_create_chart_checks_every_series_after_an_overflow(self):
        # A later series may still be refused: each one is read.
        deps, _ = self.active(rows=MANY_DEPS)
        series = [{"column_y": "n_cum_dose1"}, {"column_y": "label", "aggregate_y": "count"}]
        result = self.call("create_chart", deps, config=self.chart_config(series=series))
        assert result.more_groups is True
        assert len(self.tabular.queries) == 2

    def test_create_chart_returns_a_refused_query_as_an_error(self):
        deps, _ = self.active()
        self.tabular.fails_with(400, 'invalid input syntax for type bigint: "abc"')
        result = self.call("create_chart", deps, config=self.chart_config())
        assert result == ToolError(
            errors=['The tabular service answered 400: invalid input syntax for type bigint: "abc"']
        )

    def test_create_chart_stays_valid_when_the_service_fails_on_its_side(self, caplog):
        deps, _ = self.active()
        self.tabular.fails_with(502, "Bad Gateway")
        with caplog.at_level("WARNING", logger="udata.core.assistant.tools"):
            result = self.call("create_chart", deps, config=self.chart_config())
        assert result.status == "ok"
        assert result.more_groups is None
        assert len(self.tabular.queries) == 1
        assert "Could not check the group count" in caplog.text

    def test_create_chart_stays_valid_when_the_service_is_unavailable(self, caplog):
        deps, _ = self.active()
        self.tabular.unreachable()
        series = [{"column_y": "n_cum_dose1"}, {"column_y": "label", "aggregate_y": "count"}]
        with caplog.at_level("WARNING", logger="udata.core.assistant.tools"):
            result = self.call("create_chart", deps, config=self.chart_config(series=series))
        assert result.status == "ok"
        assert result.more_groups is None
        assert len(self.tabular.queries) == 1
        assert "Could not check the group count" in caplog.text

    # update_chart.

    def test_update_chart_returns_the_patch(self):
        result = self.call("update_chart", self.make_deps(), patch=UpdateChartInput(title="Neuf"))
        assert result == UpdateToolOutput(patch={"title": "Neuf"})

    def test_update_chart_rejects_an_empty_patch(self):
        result = self.call("update_chart", self.make_deps(), patch=UpdateChartInput())
        assert result == ToolError(errors=["At least one change is required."])


def page(rows, total=None) -> TabularPage:
    return TabularPage(data=rows, meta={"total": total})


def test_render_result_shows_at_most_one_page_of_rows():
    rows = [{"n": i} for i in range(PAGE_SIZE + 1)]
    result = _render_result(page(rows, total=PAGE_SIZE + 1))
    lines = result.table.split("\n")
    assert len(lines) == PAGE_SIZE + 1
    assert lines[-1] == str(PAGE_SIZE - 1)
    assert result.rows == PAGE_SIZE
    assert result.total == PAGE_SIZE + 1


def test_render_result_of_no_rows_is_an_empty_table():
    assert _render_result(page([], total=0)) == QueryOutput(table="", rows=0, total=0)


def test_render_result_keeps_each_row_on_one_line_and_cuts_long_cells():
    rows = [{"a|b": "x | y\nz", "long": "v" * (MAX_CELL_CHARS + 50)}]
    header, line = _render_result(page(rows)).table.split("\n")
    assert header == "a/b | long"
    assert line == f"x / y z | {'v' * MAX_CELL_CHARS}…"


def test_render_result_leaves_out_whole_rows_past_the_size_bound():
    rows = [{f"c{i}": "v" * MAX_CELL_CHARS for i in range(10)} for _ in range(PAGE_SIZE)]
    result = _render_result(page(rows, total=926))
    lines = result.table.split("\n")
    assert result.total == 926
    assert len(result.table) <= MAX_RESULT_CHARS + 200
    assert result.rows == len(lines) - 2 < PAGE_SIZE
    assert lines[-1].startswith(f"Result cut to {result.rows} rows for its size")
    assert all(line.count(" | ") == 9 for line in lines[:-1])


def test_render_result_with_too_many_columns_asks_for_fewer():
    # 400 long column names: the header alone is past the bound.
    rows = [{f"colonne_au_nom_long_{i:03}": i for i in range(400)}]
    result = _render_result(page(rows, total=12))
    assert isinstance(result, ToolError)
    [error] = result.errors
    assert len(error) <= MAX_RESULT_CHARS
    assert error.startswith("Result not shown: its 400 columns")
    assert "`columns`" in error
