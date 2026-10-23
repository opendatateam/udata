"""pydantic-ai agent wiring for the AI assistant.

The agent talks to the Albert API through an OpenAI-compatible provider
and is built for synchronous use from Flask sync workers: build it with
:func:`get_agent` inside an application context and run it with
``agent.run_sync``.
"""

from flask import current_app
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from udata.core.assistant.prompts import SYSTEM_INSTRUCTIONS
from udata.core.assistant.tools import AssistantDeps, register_tools

# How many times the agent retries a failed model call before giving up.
MODEL_RETRIES = 2


def get_agent() -> Agent[AssistantDeps, str]:
    """Build the assistant agent configured from the Flask settings."""
    model = OpenAIChatModel(
        current_app.config["AI_MODEL"],
        provider=OpenAIProvider(
            base_url=current_app.config["AI_BASE_URL"],
            api_key=current_app.config["AI_API_KEY"],
        ),
    )
    agent: Agent[AssistantDeps, str] = Agent(
        model,
        output_type=str,
        instructions=SYSTEM_INSTRUCTIONS,
        deps_type=AssistantDeps,
        retries=MODEL_RETRIES,
    )
    register_tools(agent)
    return agent
