import pytest
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from udata.core.assistant.agent import get_agent
from udata.core.assistant.data_query import MAX_QUERIES_PER_QUESTION, PAGE_SIZE
from udata.core.assistant.prompts import PROMPT_VERSION, SYSTEM_INSTRUCTIONS
from udata.core.assistant.tabular import TabularClient
from udata.core.assistant.tools import AssistantDeps
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
        assert agent.model_settings == {"max_tokens": 2048, "openai_reasoning_effort": "none"}

    def test_agent_bounds_the_output_tokens_by_default(self):
        assert get_agent().model_settings == {"max_tokens": 8192}

    def test_agent_keeps_the_provider_defaults_without_settings(self):
        self.app.config["AI_MODELS"] = [{"name": "gpt-oss-120b"}]
        assert get_agent().model_settings is None

    def test_instructions_follow_the_tool_limits(self):
        assert f"at most {MAX_QUERIES_PER_QUESTION} calls" in SYSTEM_INSTRUCTIONS
        assert f"at most {PAGE_SIZE} rows or groups" in SYSTEM_INSTRUCTIONS

    def test_the_model_receives_the_instructions_and_tool_descriptions(self):
        received = {}

        def record(messages, info: AgentInfo):
            received["instructions"] = info.instructions
            received.update({tool.name: tool.description for tool in info.function_tools})
            return ModelResponse(parts=[TextPart("ok")])

        deps = AssistantDeps(tabular=TabularClient())
        get_agent().run_sync("Bonjour", model=FunctionModel(record), deps=deps)
        assert PROMPT_VERSION in received["instructions"]
        assert f"at most {PAGE_SIZE} rows" in received["query_data"]
        assert f"more than {PAGE_SIZE} points" in received["create_chart"]
