from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from udata.core.assistant.agent import get_agent
from udata.core.assistant.data_query import MAX_QUERIES_PER_QUESTION, PAGE_SIZE
from udata.core.assistant.prompts import PROMPT_VERSION, SYSTEM_INSTRUCTIONS
from udata.core.assistant.tabular import TabularClient
from udata.core.assistant.tools import AssistantDeps
from udata.tests.api import PytestOnlyDBTestCase


class SystemPromptEchoModel(TestModel):
    """TestModel qui répond avec les instructions système reçues.

    Permet de vérifier le prompt de l'agent sans appeler le modèle réel.
    """

    def _request(self, messages, model_settings, model_request_parameters):
        instructions = "\n".join(
            part.content for part in model_request_parameters.instruction_parts
        )
        if instructions:
            return ModelResponse(parts=[TextPart(instructions)], model_name=self._model_name)
        return super()._request(messages, model_settings, model_request_parameters)


class AssistantAgentTest(PytestOnlyDBTestCase):
    def make_deps(self):
        with self.app.app_context():
            tabular = TabularClient(base_url="http://tabular.test")
        return AssistantDeps(tabular=tabular)

    def test_agent_forwards_reasoning_effort_setting(self):
        self.app.config["AI_REASONING_EFFORT"] = "none"
        agent = get_agent()
        assert agent.model_settings == {"openai_reasoning_effort": "none"}

    def test_agent_runs_with_test_model(self):
        agent = get_agent()
        result = agent.run_sync("Bonjour", model=SystemPromptEchoModel(), deps=self.make_deps())
        assert result.output
        assert PROMPT_VERSION in result.output

    def test_system_instructions_mention_core_rules(self):
        assert PROMPT_VERSION in SYSTEM_INSTRUCTIONS
        for expected in ("Markdown", "français", "NULL"):
            assert expected in SYSTEM_INSTRUCTIONS

    def test_instructions_name_the_chart_tools(self):
        for tool in ("create_chart", "update_chart", "query_data"):
            assert tool in SYSTEM_INSTRUCTIONS

    def test_instructions_follow_the_tool_limits(self):
        assert f"au plus {MAX_QUERIES_PER_QUESTION} appels" in SYSTEM_INSTRUCTIONS
        assert f"au plus {PAGE_SIZE} lignes ou groupes" in SYSTEM_INSTRUCTIONS

    def test_tool_descriptions_follow_the_page_size(self):
        # The tool definitions the model receives during a run.
        received = {}

        def record_tools(messages, info: AgentInfo):
            received.update({tool.name: tool.description for tool in info.function_tools})
            return ModelResponse(parts=[TextPart("ok")])

        get_agent().run_sync("Bonjour", model=FunctionModel(record_tools), deps=self.make_deps())
        assert f"au plus {PAGE_SIZE} lignes" in received["query_data"]
        assert f"dépasse {PAGE_SIZE} points" in received["create_chart"]
