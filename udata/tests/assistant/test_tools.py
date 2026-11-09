"""Tools attached to the AI assistant agent: tests.

Tools run in a pydantic-ai worker thread without Flask's request context:
the requesting user travels through ``AssistantDeps.user`` and permissions
are checked against an identity rebuilt from that snapshot.
"""

import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from udata.auth import login_user
from udata.core.assistant.tabular import TabularClient, TabularError
from udata.core.assistant.tools import (
    MAX_SQL_PER_QUESTION,
    MAX_STEPS,
    AssistantDeps,
    register_tools,
)
from udata.core.dataset.factories import DatasetFactory, LicenseFactory, ResourceFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.tests.api import PytestOnlyDBTestCase

SQL = "SELECT a, b FROM data"


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

    def test_registers_the_four_tools(self):
        assert set(self.tools) == {
            "get_dataset_metadata",
            "inspect_schema",
            "execute_sql",
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
                "columns": [{"name": "col_a", "type": "int"}, {"name": "col_b", "type": "str"}],
                "nb_rows": 42,
            },
        )
        result = self.call("inspect_schema", deps, resource_id=str(resource.id))
        assert "col_a" in result and "int" in result
        assert "col_b" in result and "str" in result
        assert "42" in result

    def test_inspect_schema_unknown_resource_returns_french_error(self, mocker):
        deps = self.make_deps()
        profile = mocker.patch.object(deps.tabular, "get_profile")
        result = self.call("inspect_schema", deps, resource_id=str(ResourceFactory().id))
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
        mocker.patch.object(deps.tabular, "get_profile", return_value={"nb_rows": 1})
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
        assert "Impossible" in result
        assert "tabular.example.com" not in result

    def test_execute_sql_renders_columns_and_rows(self, mocker):
        resource = self.owned_resource()
        deps = self.make_deps()
        mock = mocker.patch.object(
            deps.tabular, "execute_sql", return_value={"columns": ["a", "b"], "rows": [[1, 2]]}
        )
        result = self.call("execute_sql", deps, resource_id=str(resource.id), sql=SQL)
        assert "a" in result and "b" in result
        assert "1" in result and "2" in result
        mock.assert_called_once_with(str(resource.id), SQL)
        assert deps.sql_count == 1

    def test_execute_sql_truncates_to_first_50_rows(self, mocker):
        resource = self.owned_resource()
        deps = self.make_deps()
        rows = [[i] for i in range(60)]
        mocker.patch.object(
            deps.tabular, "execute_sql", return_value={"columns": ["a"], "rows": rows}
        )
        result = self.call("execute_sql", deps, resource_id=str(resource.id), sql=SQL)
        assert "60" in result  # mention of the total
        rendered_rows = [line for line in result.splitlines() if line.strip().isdigit()]
        assert len(rendered_rows) == 50

    def test_execute_sql_refuses_unknown_resource_before_anything(self, mocker):
        deps = self.make_deps()
        mock = mocker.patch.object(deps.tabular, "execute_sql")
        result = self.call("execute_sql", deps, resource_id=str(ResourceFactory().id), sql=SQL)
        assert "introuvable" in result
        mock.assert_not_called()
        assert deps.sql_count == 0

    def test_execute_sql_hides_resource_of_private_dataset(self, mocker):
        deps = self.make_deps()
        mock = mocker.patch.object(deps.tabular, "execute_sql")
        resource = self.owned_resource(private=True)
        result = self.call("execute_sql", deps, resource_id=str(resource.id), sql=SQL)
        assert "introuvable" in result
        mock.assert_not_called()

    def test_execute_sql_drop_table_is_refused_before_http_call(self, mocker):
        resource = self.owned_resource()
        deps = self.make_deps()
        mock = mocker.patch.object(deps.tabular, "execute_sql")
        result = self.call("execute_sql", deps, resource_id=str(resource.id), sql="DROP TABLE data")
        assert "lecture seule" in result
        assert "Statement type is not allowed" in result
        mock.assert_not_called()
        assert deps.sql_count == 0

    def test_execute_sql_refused_beyond_limit(self, mocker):
        resource = self.owned_resource()
        deps = self.make_deps()
        mock = mocker.patch.object(
            deps.tabular, "execute_sql", return_value={"columns": ["a"], "rows": [[1]]}
        )
        for _ in range(MAX_SQL_PER_QUESTION):
            result = self.call("execute_sql", deps, resource_id=str(resource.id), sql=SQL)
            assert "refusée" not in result
        result = self.call("execute_sql", deps, resource_id=str(resource.id), sql=SQL)
        assert "refusée" in result
        assert mock.call_count == MAX_SQL_PER_QUESTION
        assert deps.sql_count == MAX_SQL_PER_QUESTION

    def test_execute_sql_tabular_error_returns_sanitized_french_message(self, mocker):
        resource = self.owned_resource()
        deps = self.make_deps()
        mocker.patch.object(
            deps.tabular,
            "execute_sql",
            side_effect=TabularError("le service tabulaire a renvoyé une erreur."),
        )
        result = self.call("execute_sql", deps, resource_id=str(resource.id), sql=SQL)
        assert "échoué" in result
        assert "tabular.example.com" not in result

    def test_tool_budget_refuses_beyond_assistant_max_steps(self, mocker):
        """MAX_STEPS caps tool calls per agent run (steps proxy), independently
        of the per-question SQL limit."""
        resource = self.owned_resource()
        deps = self.make_deps()
        mocker.patch.object(deps.tabular, "get_profile", return_value={"nb_rows": 1})
        for _ in range(MAX_STEPS):
            result = self.call("inspect_schema", deps, resource_id=str(resource.id))
            assert "refusée" not in result
        result = self.call("inspect_schema", deps, resource_id=str(resource.id))
        assert "refusée" in result
        assert deps.tool_count == MAX_STEPS

    def test_tool_budget_is_shared_across_tools(self, mocker):
        """Every tool call counts against the same per-run budget."""
        resource = self.owned_resource()
        deps = self.make_deps()
        mocker.patch.object(deps.tabular, "get_profile", return_value={"nb_rows": 1})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("udata.core.assistant.tools.MAX_STEPS", 2)
            self.call("inspect_schema", deps, resource_id=str(resource.id))
            self.call("get_dataset_metadata", deps, dataset_id="0" * 24)
            result = self.call("execute_sql", deps, resource_id=str(resource.id), sql=SQL)
            assert "refusée" in result

    def test_tool_budget_resets_per_run(self, mocker):
        """A fresh AssistantDeps (a new agent run) starts with a clean budget."""
        resource = self.owned_resource()
        first = self.make_deps()
        mocker.patch.object(first.tabular, "get_profile", return_value={"nb_rows": 1})
        self.call("inspect_schema", first, resource_id=str(resource.id))
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("udata.core.assistant.tools.MAX_STEPS", 1)
            result = self.call("inspect_schema", first, resource_id=str(resource.id))
            assert "refusée" in result
        second = self.make_deps()
        mocker.patch.object(second.tabular, "get_profile", return_value={"nb_rows": 1})
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

    def test_tools_are_callable_through_the_agent(self, mocker):
        resource = self.owned_resource()
        deps = self.make_deps()
        mock = mocker.patch.object(
            deps.tabular, "execute_sql", return_value={"columns": ["a"], "rows": [[1]]}
        )

        class FixedArgsModel(TestModel):
            """TestModel that calls execute_sql with a known resource_id."""

            def gen_tool_args(self, tool_def):
                return {"resource_id": str(resource.id), "sql": SQL}

        agent = Agent(model=FixedArgsModel(call_tools=["execute_sql"]), deps_type=AssistantDeps)
        register_tools(agent)
        with self.request_as():
            result = agent.run_sync("compte les lignes", deps=deps)
        assert deps.sql_count == 1
        mock.assert_called_once_with(str(resource.id), SQL)
        assert result.output
