"""pydantic-ai agent wiring for the AI assistant.

The agent talks to the Albert API through an OpenAI-compatible provider.
Build it with :func:`get_agent` inside an application context: the chat
endpoint streams it through pydantic-ai's Vercel AI adapter.
"""

from flask import current_app
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from udata.core.assistant.prompts import SYSTEM_INSTRUCTIONS
from udata.core.assistant.tools import AssistantDeps, register_tools

# Retries the model gets for invalid tool arguments or output. A failed model call is
# retried by the OpenAI client itself (twice, on rate limits, 5xx and connection errors),
# within the turn timeout; a call still failing then ends the turn.
MODEL_RETRIES = 2


def get_agent() -> Agent[AssistantDeps, str]:
    """Build the assistant agent configured from the Flask settings."""
    model = OpenAIChatModel(
        current_app.config["AI_MODEL"],
        provider=OpenAIProvider(
            base_url=current_app.config["AI_BASE_URL"],
            # Placeholder keeps the agent buildable without a key; the endpoint
            # 503s before any run when AI_API_KEY is unset.
            api_key=current_app.config["AI_API_KEY"] or "not-configured",
        ),
    )
    model_settings: OpenAIChatModelSettings = {}
    if max_tokens := current_app.config["AI_MAX_OUTPUT_TOKENS"]:
        model_settings["max_tokens"] = max_tokens
    if effort := current_app.config["AI_REASONING_EFFORT"]:
        model_settings["openai_reasoning_effort"] = effort
    agent: Agent[AssistantDeps, str] = Agent(
        model,
        output_type=str,
        instructions=SYSTEM_INSTRUCTIONS,
        deps_type=AssistantDeps,
        retries=MODEL_RETRIES,
        model_settings=model_settings or None,
    )
    register_tools(agent)
    return agent
