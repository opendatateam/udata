"""Tools attached to the AI assistant agent: tests.

Tools run in a pydantic-ai worker thread without Flask's request context:
permissions are checked against the identity of the request context.
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
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from udata.auth import login_user
from udata.core.assistant.charts import CreateChartInput, UpdateChartInput
from udata.core.assistant.data_query import PAGE_SIZE, Filter
from udata.core.assistant.tabular import TabularClient, TabularError, TabularRequestRefused
from udata.core.assistant.tools import (
    MAX_QUERIES_PER_QUESTION,
    MAX_SERIALIZED_RESOURCES,
    MAX_STEPS,
    AssistantDeps,
    _render_result,
    register_tools,
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


class AssistantToolsTest(PytestOnlyDBTestCase):
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

    def call(self, name, deps, user=None, **kwargs):
        ctx = SimpleNamespace(deps=deps)
        with self.request_as(user):
            return self.tools[name].function(ctx, **kwargs)

    def make_deps(self, **kwargs):
        with self.app.app_context():
            tabular = TabularClient()
        return AssistantDeps(tabular=tabular, **kwargs)

    def owned_resource(self, **dataset_kwargs):
        """A resource with a dataset; public unless ``dataset_kwargs`` say otherwise."""
        resource = ResourceFactory()
        dataset_kwargs.setdefault("title", "Données de test")
        DatasetFactory(resources=[resource], **dataset_kwargs)
        return resource

    def test_registers_the_six_tools(self):
        assert set(self.tools) == {
            "get_dataset_metadata",
            "inspect_schema",
            "query_data",
            "create_chart",
            "update_chart",
            "request_clarification",
        }

    def test_get_dataset_metadata_serializes_dataset(self):
        license = LicenseFactory(title="Licence Ouverte")
        organization = OrganizationFactory(name="Ma collectivité")
        resources = ResourceFactory.build_batch(2)
        dataset = DatasetFactory(
            title="Données de test",
            license=license,
            organization=organization,
            resources=resources,
        )
        result = self.call("get_dataset_metadata", self.make_deps(), dataset_id=str(dataset.id))
        payload = json.loads(result)
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

    def test_get_dataset_metadata_caps_the_listed_resources(self):
        resources = ResourceFactory.build_batch(MAX_SERIALIZED_RESOURCES + 3)
        dataset = DatasetFactory(resources=resources)
        result = self.call("get_dataset_metadata", self.make_deps(), dataset_id=str(dataset.id))
        payload = json.loads(result)
        listed = [resource["id"] for resource in payload["resources"]]
        assert listed == [str(r.id) for r in resources[:MAX_SERIALIZED_RESOURCES]]
        assert payload["more_resources"] == "… et 3 autres"

    def test_get_dataset_metadata_of_a_dataset_stored_without_resources(self):
        dataset = DatasetFactory(title="Sans ressources")
        Dataset._get_collection().update_one({"_id": dataset.id}, {"$unset": {"resources": ""}})
        result = self.call("get_dataset_metadata", self.make_deps(), dataset_id=str(dataset.id))
        payload = json.loads(result)
        assert payload["title"] == "Sans ressources"
        assert payload["resources"] == []
        assert "more_resources" not in payload

    def test_get_dataset_metadata_unknown_id_returns_french_error(self):
        result = self.call("get_dataset_metadata", self.make_deps(), dataset_id="0" * 24)
        assert "introuvable" in result

    def test_get_dataset_metadata_hides_private_dataset_from_anonymous(self):
        dataset = DatasetFactory(title="Secret", private=True)
        result = self.call("get_dataset_metadata", self.make_deps(), dataset_id=str(dataset.id))
        assert "introuvable" in result
        assert "Secret" not in result

    def test_get_dataset_metadata_hides_private_dataset_from_other_user(self):
        dataset = DatasetFactory(title="Secret", private=True, owner=UserFactory())
        other = UserFactory()
        result = self.call(
            "get_dataset_metadata",
            self.make_deps(),
            user=other,
            dataset_id=str(dataset.id),
        )
        assert "introuvable" in result
        assert "Secret" not in result

    def test_get_dataset_metadata_hides_deleted_dataset(self):
        from datetime import UTC, datetime

        dataset = DatasetFactory(title="Supprimé", deleted=datetime.now(UTC))
        result = self.call("get_dataset_metadata", self.make_deps(), dataset_id=str(dataset.id))
        assert "introuvable" in result
        assert "Supprimé" not in result

    def test_get_dataset_metadata_owner_sees_own_private_dataset(self):
        owner = UserFactory()
        dataset = DatasetFactory(title="Secret", private=True, owner=owner)
        result = self.call(
            "get_dataset_metadata",
            self.make_deps(),
            user=owner,
            dataset_id=str(dataset.id),
        )
        payload = json.loads(result)
        assert payload["title"] == "Secret"

    def test_inspect_schema_lists_columns_types_and_rows(self, mocker):
        resource = self.owned_resource()
        deps = self.make_deps()
        mocker.patch.object(
            deps.tabular,
            "get_profile",
            return_value={
                "profile": {
                    "header": ["col_a", "col_b"],
                    "columns": {
                        "col_b": {"python_type": "string"},
                        "col_a": {"python_type": "int"},
                    },
                    "total_lines": 42,
                }
            },
        )
        result = self.call("inspect_schema", deps, resource_id=str(resource.id))
        assert "- col_a (int)\n- col_b (string)" in result
        assert "Nombre de lignes : 42" in result

    @pytest.mark.parametrize(
        "profile",
        [
            ["not", "a", "dict"],
            {"profile": "x"},
            {"profile": {"header": [["unhashable"]], "columns": {}}},
            {"profile": {"header": "dep", "columns": []}},
            {"profile": {"columns": {"dep": "string"}, "total_lines": {"n": 1}}},
        ],
    )
    def test_inspect_schema_survives_a_malformed_profile(self, mocker, profile):
        resource = self.owned_resource()
        deps = self.make_deps()
        mocker.patch.object(deps.tabular, "get_profile", return_value=profile)
        result = self.call("inspect_schema", deps, resource_id=str(resource.id))
        assert result == "Aucune information de colonne disponible."

    def test_inspect_schema_unknown_resource_returns_french_error(self, mocker):
        deps = self.make_deps()
        profile = mocker.patch.object(deps.tabular, "get_profile")
        result = self.call("inspect_schema", deps, resource_id=str(ResourceFactory().id))
        assert "introuvable" in result
        profile.assert_not_called()

    def test_inspect_schema_refuses_a_resource_id_shared_by_several_datasets(self, mocker):
        shared_id = uuid4()
        DatasetFactory(resources=[ResourceFactory(id=shared_id)])
        DatasetFactory(resources=[ResourceFactory(id=shared_id)])
        deps = self.make_deps()
        profile = mocker.patch.object(deps.tabular, "get_profile")
        result = self.call("inspect_schema", deps, resource_id=str(shared_id))
        assert "introuvable" in result
        profile.assert_not_called()

    def test_inspect_schema_hides_resource_of_private_dataset(self, mocker):
        deps = self.make_deps()
        profile = mocker.patch.object(deps.tabular, "get_profile")
        resource = self.owned_resource(private=True)
        result = self.call("inspect_schema", deps, resource_id=str(resource.id))
        assert "introuvable" in result
        profile.assert_not_called()

    def test_inspect_schema_hides_resource_of_deleted_dataset(self, mocker):
        from datetime import UTC, datetime

        deps = self.make_deps()
        profile = mocker.patch.object(deps.tabular, "get_profile")
        resource = self.owned_resource(deleted=datetime.now(UTC))
        result = self.call("inspect_schema", deps, resource_id=str(resource.id))
        assert "introuvable" in result
        profile.assert_not_called()

    def test_inspect_schema_owner_of_private_dataset_is_allowed(self, mocker):
        owner = UserFactory()
        resource = self.owned_resource(private=True, owner=owner)
        deps = self.make_deps()
        mocker.patch.object(
            deps.tabular, "get_profile", return_value={"profile": {"total_lines": 1}}
        )
        result = self.call("inspect_schema", deps, user=owner, resource_id=str(resource.id))
        assert "introuvable" not in result

    def test_inspect_schema_tabular_error_returns_sanitized_french_message(self, mocker):
        resource = self.owned_resource()
        deps = self.make_deps()
        mocker.patch.object(
            deps.tabular,
            "get_profile",
            side_effect=TabularError("le service tabulaire a renvoyé une erreur."),
        )
        result = self.call("inspect_schema", deps, resource_id=str(resource.id))
        assert result == "Le service tabulaire est indisponible."
        assert "tabular.example.com" not in result

    def test_tool_budget_refuses_beyond_assistant_max_steps(self, mocker):
        """MAX_STEPS caps tool calls per agent run (steps proxy), independently
        of the per-question query limit."""
        resource = self.owned_resource()
        deps = self.make_deps()
        mocker.patch.object(
            deps.tabular, "get_profile", return_value={"profile": {"total_lines": 1}}
        )
        for _ in range(MAX_STEPS):
            result = self.call("inspect_schema", deps, resource_id=str(resource.id))
            assert "refusée" not in result
        result = self.call("inspect_schema", deps, resource_id=str(resource.id))
        assert "refusée" in result
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
        deps = SlowCountersDeps(tabular=self.make_deps().tabular)
        results = self._race(
            "request_clarification", deps, 2 * MAX_STEPS, question="?", choices=["a", "b"]
        )
        assert sum("refusée" not in result for result in results) == MAX_STEPS

    def test_query_budget_holds_under_parallel_calls(self, mocker):
        resource = self.owned_resource()
        deps = SlowCountersDeps(tabular=self.make_deps().tabular, resource_id=str(resource.id))
        mocker.patch.object(deps.tabular, "get_profile", return_value=self.PROFILE)
        mocker.patch.object(deps.tabular, "get_data", return_value={"data": []})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("udata.core.assistant.tools.MAX_STEPS", 100)
            results = self._race("query_data", deps, 2 * MAX_QUERIES_PER_QUESTION)
        assert sum("refusée" not in result for result in results) == MAX_QUERIES_PER_QUESTION

    def test_tool_budget_is_shared_across_tools(self, mocker):
        """Every tool call counts against the same per-run budget."""
        resource = self.owned_resource()
        deps = self.make_deps()
        mocker.patch.object(
            deps.tabular, "get_profile", return_value={"profile": {"total_lines": 1}}
        )
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("udata.core.assistant.tools.MAX_STEPS", 2)
            self.call("inspect_schema", deps, resource_id=str(resource.id))
            self.call("get_dataset_metadata", deps, dataset_id="0" * 24)
            result = self.call("request_clarification", deps, question="?", choices=[])
            assert "refusée" in result

    def test_tool_budget_resets_per_run(self, mocker):
        """A fresh AssistantDeps (a new agent run) starts with a clean budget."""
        resource = self.owned_resource()
        first = self.make_deps()
        mocker.patch.object(
            first.tabular, "get_profile", return_value={"profile": {"total_lines": 1}}
        )
        self.call("inspect_schema", first, resource_id=str(resource.id))
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("udata.core.assistant.tools.MAX_STEPS", 1)
            result = self.call("inspect_schema", first, resource_id=str(resource.id))
            assert "refusée" in result
        second = self.make_deps()
        mocker.patch.object(
            second.tabular, "get_profile", return_value={"profile": {"total_lines": 1}}
        )
        result = self.call("inspect_schema", second, resource_id=str(resource.id))
        assert "refusée" not in result

    def test_request_clarification_numbers_choices(self):
        result = self.call(
            "request_clarification",
            self.make_deps(),
            question="Laquelle ?",
            choices=["Paris", "Lyon"],
        )
        assert "Laquelle ?" in result
        assert "1. Paris" in result
        assert "2. Lyon" in result

    PROFILE = {
        "profile": {
            "header": ["dep", "n_cum_dose1", "label"],
            "columns": {
                "dep": {"python_type": "string"},
                "n_cum_dose1": {"python_type": "int"},
                "label": {"python_type": "string"},
            },
            "total_lines": 10,
        }
    }

    def active(self, mocker, **kwargs):
        """Deps on a readable resource, with the profile mocked."""
        resource = self.owned_resource()
        deps = self.make_deps(resource_id=str(resource.id), **kwargs)
        mocker.patch.object(deps.tabular, "get_profile", return_value=self.PROFILE)
        return deps, resource

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

    def test_query_data_requires_an_active_resource(self):
        result = self.call("query_data", self.make_deps())
        assert "Aucune ressource active" in result

    def test_query_data_groups_and_sorts_on_x(self, mocker):
        deps, resource = self.active(mocker)
        get_data = mocker.patch.object(
            deps.tabular, "get_data", return_value={"data": [{"dep": "01", "n_cum_dose1__max": 3}]}
        )
        result = self.call(
            "query_data", deps, groupby="dep", aggregate_column="n_cum_dose1", aggregate="max"
        )
        get_data.assert_called_once_with(
            str(resource.id), "dep__groupby&n_cum_dose1__max&dep__sort=asc&page=1&page_size=50"
        )
        assert "dep | n_cum_dose1__max" in result
        assert "01 | 3" in result

    def test_query_data_reports_more_than_50_groups(self, mocker):
        deps, _ = self.active(mocker)
        rows = [{"dep": str(i), "n_cum_dose1__max": i} for i in range(50)]
        mocker.patch.object(deps.tabular, "get_data", return_value={"data": rows})
        more = mocker.patch.object(deps.tabular, "has_more_groups", return_value=True)
        result = self.call(
            "query_data", deps, groupby="dep", aggregate_column="n_cum_dose1", aggregate="max"
        )
        # cdata parses this exact sentence
        assert result.endswith("\nPlus de 50 groupes : seuls les 50 premiers sont pris en compte.")
        more.assert_called_once()

    def test_query_data_reports_the_total_of_truncated_rows(self, mocker):
        deps, _ = self.active(mocker)
        rows = [{"dep": str(i)} for i in range(PAGE_SIZE)]
        mocker.patch.object(
            deps.tabular, "get_data", return_value={"data": rows, "meta": {"total": 926}}
        )
        more = mocker.patch.object(deps.tabular, "has_more_groups")
        count = mocker.patch.object(deps.tabular, "row_count")
        result = self.call("query_data", deps, columns=["dep"])
        assert result.endswith(
            "\nRésultat tronqué : 926 lignes au total, 50 premières lignes affichées."
        )
        more.assert_not_called()
        count.assert_not_called()

    def test_query_data_does_not_probe_a_partial_page_of_groups(self, mocker):
        deps, _ = self.active(mocker)
        rows = [{"dep": str(i), "n_cum_dose1__max": i} for i in range(15)]
        mocker.patch.object(deps.tabular, "get_data", return_value={"data": rows})
        more = mocker.patch.object(deps.tabular, "has_more_groups")
        result = self.call(
            "query_data", deps, groupby="dep", aggregate_column="n_cum_dose1", aggregate="max"
        )
        assert "Plus de" not in result
        more.assert_not_called()

    def test_query_data_allows_a_global_aggregate(self, mocker):
        deps, resource = self.active(mocker)
        get_data = mocker.patch.object(
            deps.tabular, "get_data", return_value={"data": [{"n_cum_dose1__sum": 5}]}
        )
        more = mocker.patch.object(deps.tabular, "has_more_groups")
        result = self.call("query_data", deps, aggregate_column="n_cum_dose1", aggregate="sum")
        get_data.assert_called_once_with(str(resource.id), "n_cum_dose1__sum&page=1&page_size=50")
        more.assert_not_called()
        assert "n_cum_dose1__sum" in result

    def test_query_data_refuses_groupby_without_aggregate(self, mocker):
        deps, _ = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data")
        result = self.call("query_data", deps, groupby="dep")
        assert "groupby demande un agrégat" in result
        get_data.assert_not_called()

    def test_query_data_refuses_columns_with_an_aggregate(self, mocker):
        deps, _ = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data", return_value={"data": []})
        get_profile = mocker.patch.object(deps.tabular, "get_profile")
        result = self.call(
            "query_data",
            deps,
            groupby="dep",
            aggregate_column="n_cum_dose1",
            aggregate="sum",
            columns=["dep"],
        )
        assert result == (
            "Requête invalide : columns ne peut pas être combiné avec un agrégat ; retire columns."
        )
        get_data.assert_not_called()
        get_profile.assert_not_called()
        assert deps.tool_count == 1
        assert deps.query_count == 0
        self.call("query_data", deps)
        assert deps.query_count == 1

    def test_query_data_refuses_sorting_on_an_aggregated_column(self, mocker):
        deps, _ = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data", return_value={"data": []})
        mocker.patch.object(deps.tabular, "has_more_groups", return_value=False)
        get_profile = mocker.patch.object(deps.tabular, "get_profile")
        result = self.call(
            "query_data",
            deps,
            groupby="dep",
            aggregate_column="n_cum_dose1",
            aggregate="sum",
            sort_column="n_cum_dose1",
            sort_direction="desc",
        )
        assert "le tri n'est possible que sur la colonne groupby" in result
        assert "sort_x_by=axis_y" in result
        get_data.assert_not_called()
        get_profile.assert_not_called()
        assert deps.tool_count == 1
        assert deps.query_count == 0
        get_profile.side_effect = lambda *a, **k: self.PROFILE
        ok = self.call(
            "query_data",
            deps,
            groupby="dep",
            aggregate_column="n_cum_dose1",
            aggregate="sum",
            sort_column="dep",
        )
        assert "invalide" not in ok
        get_data.assert_called_once()
        assert deps.query_count == 1

    def test_query_data_refuses_a_global_aggregate_with_a_sort(self, mocker):
        deps, _ = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data")
        get_profile = mocker.patch.object(deps.tabular, "get_profile")
        result = self.call(
            "query_data",
            deps,
            aggregate_column="n_cum_dose1",
            aggregate="sum",
            sort_column="dep",
        )
        assert "le tri n'est possible que sur la colonne groupby" in result
        get_data.assert_not_called()
        get_profile.assert_not_called()
        assert deps.query_count == 0

    def test_query_data_rejects_an_unknown_column(self, mocker):
        deps, _ = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data")
        result = self.call("query_data", deps, sort_column="foo")
        assert "Colonne inconnue : foo." in result
        get_data.assert_not_called()

    def test_query_data_feeds_the_service_refusal_back(self, mocker):
        deps, _ = self.active(mocker)
        mocker.patch.object(
            deps.tabular, "get_data", side_effect=TabularRequestRefused("bad param")
        )
        result = self.call("query_data", deps)
        assert result == "Requête refusée par le service tabulaire : bad param."

    def test_query_data_tabular_error_is_a_french_message(self, mocker):
        deps, _ = self.active(mocker)
        mocker.patch.object(deps.tabular, "get_data", side_effect=TabularError("english"))
        result = self.call("query_data", deps)
        assert result == "Le service tabulaire est indisponible."

    def test_query_data_hides_resource_of_private_dataset(self, mocker):
        resource = self.owned_resource(private=True)
        deps = self.make_deps(resource_id=str(resource.id))
        profile = mocker.patch.object(deps.tabular, "get_profile")
        result = self.call("query_data", deps)
        assert "introuvable" in result
        profile.assert_not_called()

    def test_query_data_caps_queries_per_question(self, mocker):
        deps, _ = self.active(mocker)
        mocker.patch.object(deps.tabular, "get_data", return_value={"data": []})
        for _ in range(MAX_QUERIES_PER_QUESTION):
            assert "refusée" not in self.call("query_data", deps)
        result = self.call("query_data", deps)
        assert result == "Requête refusée : la limite de 3 requêtes par question est atteinte."

    def test_create_chart_returns_the_validated_chart(self, mocker):
        deps, resource = self.active(mocker)
        more = mocker.patch.object(deps.tabular, "has_more_groups", return_value=False)
        result = self.call("create_chart", deps, config=self.chart_config())
        more.assert_called_once()
        assert result["status"] == "ok"
        assert result["chart"]["series"][0]["resource_id"] == str(resource.id)
        assert result["more_groups"] is False

    def test_create_chart_returns_errors_for_an_invalid_config(self, mocker):
        deps, _ = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data")
        config = self.chart_config(x_axis={"column_x": "foo", "type": "discrete"})
        result = self.call("create_chart", deps, config=config)
        assert result == {"status": "error", "errors": ["Colonne inconnue : foo."]}
        get_data.assert_not_called()

    def test_query_data_refuses_a_filter_without_value_without_using_a_query(self, mocker):
        deps, _ = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data")
        flt = {"column": "dep", "condition": "exact", "value": ""}
        result = self.call("query_data", deps, filters=Filter(**flt))
        assert result == "Le filtre exact sur dep demande une valeur."
        get_data.assert_not_called()
        assert deps.query_count == 0

    def test_query_data_refuses_a_numeric_aggregate_on_text_without_using_a_query(self, mocker):
        deps, _ = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data")
        result = self.call(
            "query_data", deps, groupby="dep", aggregate_column="label", aggregate="sum"
        )
        assert result == "L'agrégat sum demande une colonne numérique : label est de type string."
        get_data.assert_not_called()
        assert deps.query_count == 0

    @pytest.mark.parametrize("aggregate", ["min", "max"])
    def test_query_data_allows_min_max_on_a_text_column(self, mocker, aggregate):
        # Exploring, e.g. the latest date of a column api-tabular types as string.
        deps, resource = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data", return_value={"data": []})
        self.call("query_data", deps, aggregate_column="label", aggregate=aggregate)
        get_data.assert_called_once_with(
            str(resource.id), f"label__{aggregate}&page=1&page_size=50"
        )

    def test_query_data_refuses_avg_on_a_text_column(self, mocker):
        deps, _ = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data")
        result = self.call("query_data", deps, aggregate_column="label", aggregate="avg")
        assert result == "L'agrégat avg demande une colonne numérique : label est de type string."
        get_data.assert_not_called()

    def test_query_data_counts_a_text_column(self, mocker):
        deps, _ = self.active(mocker)
        mocker.patch.object(deps.tabular, "get_data", return_value={"data": []})
        result = self.call(
            "query_data", deps, groupby="dep", aggregate_column="label", aggregate="count"
        )
        assert "numérique" not in result
        assert deps.query_count == 1

    def test_create_chart_refuses_a_filter_without_value(self, mocker):
        deps, _ = self.active(mocker)
        config = self.chart_config(filters={"column": "dep", "condition": "greater"})
        result = self.call("create_chart", deps, config=config)
        assert result == {
            "status": "error",
            "errors": ["Le filtre greater sur dep demande une valeur."],
        }

    def test_create_chart_requires_an_active_resource(self):
        result = self.call("create_chart", self.make_deps(), config=self.chart_config())
        assert result["status"] == "error"
        assert "Aucune ressource active" in result["errors"][0]

    def test_create_chart_flags_more_groups(self, mocker):
        deps, resource = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data")
        more = mocker.patch.object(deps.tabular, "has_more_groups", return_value=True)
        result = self.call("create_chart", deps, config=self.chart_config())
        assert result["more_groups"] is True
        get_data.assert_not_called()
        more.assert_called_once_with(
            str(resource.id), "dep__groupby&n_cum_dose1__max&dep__sort=asc"
        )

    def profile_with_distinct_x(self, nb_distinct, nb_missing_values=0):
        """PROFILE whose X column `dep` has these csv-detective statistics."""
        stats = {"dep": {"nb_distinct": nb_distinct, "nb_missing_values": nb_missing_values}}
        return {"profile": {**self.PROFILE["profile"], "profile": stats}}

    @pytest.mark.parametrize(
        "nb_distinct,nb_missing_values,expected",
        [(926, 0, True), (51, 0, True), (50, 0, False), (50, 2, True), (49, 1, False)],
    )
    def test_create_chart_counts_unfiltered_groups_from_the_profile(
        self, mocker, nb_distinct, nb_missing_values, expected
    ):
        # One group per distinct X value, plus one for the missing values.
        deps, _ = self.active(mocker)
        deps.tabular.get_profile.return_value = self.profile_with_distinct_x(
            nb_distinct, nb_missing_values
        )
        get_data = mocker.patch.object(deps.tabular, "get_data")
        more = mocker.patch.object(deps.tabular, "has_more_groups")
        count = mocker.patch.object(deps.tabular, "row_count")
        result = self.call("create_chart", deps, config=self.chart_config())
        assert result["more_groups"] is expected
        get_data.assert_not_called()
        more.assert_not_called()
        count.assert_not_called()

    def test_create_chart_probes_filtered_groups_despite_the_profile(self, mocker):
        # The profile counts the whole table, not the filtered rows.
        deps, resource = self.active(mocker)
        deps.tabular.get_profile.return_value = self.profile_with_distinct_x(926)
        more = mocker.patch.object(deps.tabular, "has_more_groups", return_value=False)
        config = self.chart_config(filters={"column": "dep", "condition": "less", "value": "15"})
        result = self.call("create_chart", deps, config=config)
        assert result["more_groups"] is False
        more.assert_called_once_with(
            str(resource.id), "dep__groupby&n_cum_dose1__max&dep__sort=asc&dep__less=15"
        )

    def test_create_chart_ignores_a_filter_that_sends_no_condition(self, mocker):
        deps, _ = self.active(mocker)
        deps.tabular.get_profile.return_value = self.profile_with_distinct_x(926)
        more = mocker.patch.object(deps.tabular, "has_more_groups")
        config = self.chart_config(filters={"_cls": "AndFilters", "filters": []})
        result = self.call("create_chart", deps, config=config)
        assert result["more_groups"] is True
        more.assert_not_called()

    @pytest.mark.parametrize("total,expected", [(926, True), (51, True), (50, False), (14, False)])
    def test_create_chart_counts_the_rows_of_a_non_aggregated_series(self, mocker, total, expected):
        deps, resource = self.active(mocker)
        count = mocker.patch.object(deps.tabular, "row_count", return_value=total)
        more = mocker.patch.object(deps.tabular, "has_more_groups")
        config = self.chart_config(series=[{"column_y": "n_cum_dose1"}])
        result = self.call("create_chart", deps, config=config)
        assert result["more_groups"] is expected
        count.assert_called_once_with(str(resource.id), "columns=dep,n_cum_dose1&dep__sort=asc")
        more.assert_not_called()

    def test_create_chart_probes_a_non_aggregated_series_without_a_total(self, mocker):
        deps, resource = self.active(mocker)
        mocker.patch.object(deps.tabular, "row_count", return_value=None)
        more = mocker.patch.object(deps.tabular, "has_more_groups", return_value=True)
        config = self.chart_config(series=[{"column_y": "n_cum_dose1"}])
        result = self.call("create_chart", deps, config=config)
        assert result["more_groups"] is True
        more.assert_called_once_with(str(resource.id), "columns=dep,n_cum_dose1&dep__sort=asc")

    def test_create_chart_flags_more_groups_from_a_non_aggregated_series(self, mocker):
        # 15 X values, but the raw series returns its 13 890 rows, truncated by the viewer.
        deps, resource = self.active(mocker)
        count = mocker.patch.object(deps.tabular, "row_count", return_value=13_890)
        more = mocker.patch.object(deps.tabular, "has_more_groups", return_value=False)
        series = [{"column_y": "n_cum_dose1"}, {"column_y": "n_cum_dose1", "aggregate_y": "sum"}]
        result = self.call("create_chart", deps, config=self.chart_config(series=series))
        assert result["more_groups"] is True
        count.assert_called_once_with(str(resource.id), "columns=dep,n_cum_dose1&dep__sort=asc")
        more.assert_not_called()

    def test_create_chart_probes_every_series_like_the_viewer(self, mocker):
        deps, resource = self.active(mocker)
        count = mocker.patch.object(deps.tabular, "row_count", return_value=10)
        more = mocker.patch.object(deps.tabular, "has_more_groups", return_value=False)
        series = [
            {"column_y": "label", "aggregate_y": "count"},
            {"column_y": "n_cum_dose1"},
            {"column_y": "n_cum_dose1", "aggregate_y": "sum"},
            {"column_y": "n_cum_dose1", "aggregate_y": "sum"},
        ]
        result = self.call("create_chart", deps, config=self.chart_config(series=series))
        assert result["more_groups"] is False
        rid = str(resource.id)
        count.assert_called_once_with(rid, "columns=dep,n_cum_dose1&dep__sort=asc")
        assert more.call_args_list == [
            mocker.call(rid, "dep__groupby&label__count&dep__sort=asc"),
            mocker.call(rid, "dep__groupby&n_cum_dose1__sum&dep__sort=asc"),
        ]

    def test_create_chart_stops_probing_once_the_service_fails(self, mocker):
        deps, _ = self.active(mocker)
        count = mocker.patch.object(deps.tabular, "row_count", side_effect=TabularError("x"))
        more = mocker.patch.object(deps.tabular, "has_more_groups")
        series = [{"column_y": "n_cum_dose1"}, {"column_y": "label", "aggregate_y": "count"}]
        result = self.call("create_chart", deps, config=self.chart_config(series=series))
        assert result["more_groups"] is False
        count.assert_called_once()
        more.assert_not_called()

    def test_create_chart_stays_valid_when_the_group_check_fails(self, mocker):
        deps, _ = self.active(mocker)
        mocker.patch.object(deps.tabular, "has_more_groups", side_effect=TabularError("x"))
        result = self.call("create_chart", deps, config=self.chart_config())
        assert result["status"] == "ok"
        assert result["more_groups"] is False

    def test_update_chart_returns_the_patch(self):
        result = self.call("update_chart", self.make_deps(), patch=UpdateChartInput(title="Neuf"))
        assert result == {"status": "ok", "patch": {"title": "Neuf"}}

    def test_update_chart_rejects_an_empty_patch(self):
        result = self.call("update_chart", self.make_deps(), patch=UpdateChartInput())
        assert result["status"] == "error"

    def test_request_clarification_bounds_choices_to_2_to_4(self):
        schema = self.tools["request_clarification"].tool_def.parameters_json_schema
        choices = schema["properties"]["choices"]
        assert choices["minItems"] == 2
        assert choices["maxItems"] == 4

    def test_query_data_accepts_a_numeric_filter_without_cls(self, mocker):
        deps, resource = self.active(mocker)
        get_data = mocker.patch.object(deps.tabular, "get_data", return_value={"data": []})
        flt = {"column": "n_cum_dose1", "condition": "greater", "value": 2.5}

        async def call_query_data(messages, info):
            if any(getattr(p, "part_kind", "") == "tool-return" for m in messages for p in m.parts):
                return ModelResponse(parts=[TextPart("ok")])
            args = json.dumps({"filters": flt})
            return ModelResponse(parts=[ToolCallPart("query_data", args)])

        agent = Agent(model=FunctionModel(call_query_data), deps_type=AssistantDeps)
        register_tools(agent)
        with self.request_as():
            agent.run_sync("filtre", deps=deps)
        get_data.assert_called_once_with(
            str(resource.id), "n_cum_dose1__greater=2.5&page=1&page_size=50"
        )

    def test_tools_are_callable_through_the_agent(self, mocker):
        deps, _ = self.active(mocker)
        mocker.patch.object(deps.tabular, "get_data", return_value={"data": [{"a": 1}]})
        agent = Agent(model=TestModel(call_tools=["query_data"]), deps_type=AssistantDeps)
        register_tools(agent)
        with self.request_as():
            result = agent.run_sync("compte", deps=deps)
        assert deps.query_count == 1
        assert result.output


def test_render_result_shows_at_most_one_page_of_rows():
    rows = [{"n": i} for i in range(PAGE_SIZE + 1)]
    lines = _render_result({"data": rows}).split("\n")
    assert lines[PAGE_SIZE] == str(PAGE_SIZE - 1)
    assert (
        lines[-1]
        == f"Résultat tronqué : {PAGE_SIZE + 1} lignes au total, 50 premières lignes affichées."
    )
