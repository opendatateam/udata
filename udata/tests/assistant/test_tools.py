import json
from types import SimpleNamespace

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from udata.core.assistant.tabular import TabularClient, TabularError
from udata.core.assistant.tools import AssistantDeps, register_tools
from udata.core.dataset.factories import DatasetFactory, LicenseFactory, ResourceFactory
from udata.core.organization.factories import OrganizationFactory
from udata.tests.api import PytestOnlyDBTestCase

RESOURCE_ID = "5c4ae7a0e3f14a3f8b1d2e9f"
SQL = "SELECT a, b FROM data"


class AssistantToolsTest(PytestOnlyDBTestCase):
    def setup_method(self, method):
        self.agent = Agent(model=TestModel(), deps_type=AssistantDeps)
        register_tools(self.agent)
        self.tools = self.agent._function_toolset.tools

    def call(self, name, deps, **kwargs):
        ctx = SimpleNamespace(deps=deps)
        with self.app.app_context():
            return self.tools[name].function(ctx, **kwargs)

    def make_deps(self, **kwargs):
        with self.app.app_context():
            tabular = TabularClient()
        return AssistantDeps(tabular=tabular, **kwargs)

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

    def test_inspect_schema_lists_columns_types_and_rows(self, mocker):
        deps = self.make_deps()
        mocker.patch.object(
            deps.tabular,
            "get_profile",
            return_value={
                "columns": [{"name": "col_a", "type": "int"}, {"name": "col_b", "type": "str"}],
                "nb_rows": 42,
            },
        )
        result = self.call("inspect_schema", deps, resource_id=RESOURCE_ID)
        assert "col_a" in result and "int" in result
        assert "col_b" in result and "str" in result
        assert "42" in result

    def test_inspect_schema_tabular_error_returns_french_message(self, mocker):
        deps = self.make_deps()
        mocker.patch.object(deps.tabular, "get_profile", side_effect=TabularError("boom"))
        result = self.call("inspect_schema", deps, resource_id=RESOURCE_ID)
        assert "Impossible" in result
        assert "boom" in result

    def test_execute_sql_renders_columns_and_rows(self, mocker):
        deps = self.make_deps()
        mock = mocker.patch.object(
            deps.tabular, "execute_sql", return_value={"columns": ["a", "b"], "rows": [[1, 2]]}
        )
        result = self.call("execute_sql", deps, resource_id=RESOURCE_ID, sql=SQL)
        assert "a" in result and "b" in result
        assert "1" in result and "2" in result
        mock.assert_called_once_with(RESOURCE_ID, SQL)
        assert deps.sql_count == 1

    def test_execute_sql_truncates_to_first_50_rows(self, mocker):
        deps = self.make_deps()
        rows = [[i] for i in range(60)]
        mocker.patch.object(
            deps.tabular, "execute_sql", return_value={"columns": ["a"], "rows": rows}
        )
        result = self.call("execute_sql", deps, resource_id=RESOURCE_ID, sql=SQL)
        assert "60" in result  # mention of the total
        rendered_rows = [line for line in result.splitlines() if line.strip().isdigit()]
        assert len(rendered_rows) == 50

    def test_execute_sql_drop_table_is_refused_before_http_call(self, mocker):
        deps = self.make_deps()
        mock = mocker.patch.object(deps.tabular, "execute_sql")
        result = self.call("execute_sql", deps, resource_id=RESOURCE_ID, sql="DROP TABLE data")
        assert "lecture seule" in result
        mock.assert_not_called()
        assert deps.sql_count == 0

    def test_execute_sql_refused_beyond_limit(self, mocker):
        deps = self.make_deps()
        mock = mocker.patch.object(
            deps.tabular, "execute_sql", return_value={"columns": ["a"], "rows": [[1]]}
        )
        for _ in range(3):
            result = self.call("execute_sql", deps, resource_id=RESOURCE_ID, sql=SQL)
            assert "refusée" not in result
        result = self.call("execute_sql", deps, resource_id=RESOURCE_ID, sql=SQL)
        assert "refusée" in result
        assert mock.call_count == 3
        assert deps.sql_count == 3

    def test_execute_sql_tabular_error_returns_french_message(self, mocker):
        deps = self.make_deps()
        mocker.patch.object(deps.tabular, "execute_sql", side_effect=TabularError("boom"))
        result = self.call("execute_sql", deps, resource_id=RESOURCE_ID, sql=SQL)
        assert "échoué" in result
        assert "boom" in result

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
        deps = self.make_deps()
        mocker.patch.object(
            deps.tabular, "execute_sql", return_value={"columns": ["a"], "rows": [[1]]}
        )
        agent = Agent(model=TestModel(call_tools=["execute_sql"]), deps_type=AssistantDeps)
        register_tools(agent)
        with self.app.app_context():
            result = agent.run_sync("compte les lignes", deps=deps)
        assert deps.sql_count == 1
        assert result.output
