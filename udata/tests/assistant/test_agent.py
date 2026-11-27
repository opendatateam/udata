import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from udata.core.assistant.agent import get_agent
from udata.core.assistant.prompts import SYSTEM_INSTRUCTIONS, language_instructions
from udata.core.assistant.tabular import TabularClient
from udata.core.assistant.tools import AssistantDeps
from udata.http import user_agent
from udata.tests.api import PytestOnlyDBTestCase


@pytest.mark.options(AI_API_KEY="test-key")
class AssistantAgentTest(PytestOnlyDBTestCase):
    def test_agent_uses_the_first_model_and_its_settings(self):
        self.app.config["AI_MODELS"] = [
            {"name": "first", "max_output_tokens": 2048, "reasoning_effort": "none"},
            {"name": "second", "max_output_tokens": 1024},
        ]
        agent = get_agent()
        assert agent.model.model_name == "first"
        assert agent.model_settings == {
            "extra_headers": {"User-Agent": user_agent("assistant")},
            "max_tokens": 2048,
            "openai_reasoning_effort": "none",
        }

    def test_agent_bounds_the_output_tokens_by_default(self):
        assert get_agent().model_settings["max_tokens"] == 8192

    def test_agent_only_identifies_itself_without_settings(self):
        self.app.config["AI_MODELS"] = [{"name": "gpt-oss-120b"}]
        assert get_agent().model_settings == {
            "extra_headers": {"User-Agent": user_agent("assistant")}
        }

    def test_the_model_receives_the_instructions_and_tool_descriptions(self):
        received = {}

        def record(messages, info: AgentInfo):
            received["instructions"] = info.instructions
            received.update({tool.name: tool.description for tool in info.function_tools})
            return ModelResponse(parts=[TextPart("ok")])

        deps = AssistantDeps(tabular=TabularClient())
        get_agent().run_sync("Bonjour", model=FunctionModel(record), deps=deps)
        assert SYSTEM_INSTRUCTIONS in received["instructions"]
        assert received["query_data"]
        assert received["create_chart"]

    def test_query_data_asks_for_a_purpose_without_requiring_it(self):
        schemas = {}

        def record(messages, info: AgentInfo):
            schemas.update({tool.name: tool.parameters_json_schema for tool in info.function_tools})
            return ModelResponse(parts=[TextPart("ok")])

        deps = AssistantDeps(tabular=TabularClient())
        get_agent().run_sync("Bonjour", model=FunctionModel(record), deps=deps)
        schema = schemas["query_data"]
        assert schema["properties"]["purpose"]["description"]
        assert "purpose" not in schema.get("required", [])


def test_the_language_rule_covers_the_query_purpose():
    assert "purposes" in language_instructions("fr")
