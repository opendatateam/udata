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
from udata.http import user_agent

# Retries the model gets for invalid tool arguments or output. A failed model call is
# retried by the OpenAI client itself (twice, on rate limits, 5xx and connection errors),
# within the turn timeout; a call still failing then ends the turn.
MODEL_RETRIES = 2


class UnknownModel(ValueError):
    """The requested model is not one of the configured `AI_MODELS`."""


def find_model(name: str) -> dict:
    """Return the `AI_MODELS` entry named `name`."""
    for model_config in current_app.config["AI_MODELS"]:
        if model_config["name"] == name:
            return model_config
    raise UnknownModel(name)


def default_model() -> dict:
    """The first `AI_MODELS` entry."""
    return current_app.config["AI_MODELS"][0]


def offered_models() -> list[dict]:
    """The models offered to the user, in `AI_MODELS` order, the first being the default."""
    return [
        {"id": m["name"], "label": m.get("label") or m["name"]}
        for m in current_app.config["AI_MODELS"]
    ]


def get_agent(model_config: dict) -> Agent[AssistantDeps, str]:
    """Build the assistant agent for an `AI_MODELS` entry."""
    model = OpenAIChatModel(
        model_config["name"],
        provider=OpenAIProvider(
            base_url=current_app.config["AI_BASE_URL"],
            api_key=current_app.config["AI_API_KEY"],
        ),
    )
    # pydantic-ai sets its own User-Agent on each request: only a per-request header replaces it.
    model_settings: OpenAIChatModelSettings = {
        "extra_headers": {"User-Agent": user_agent("assistant")}
    }
    if max_tokens := model_config.get("max_output_tokens"):
        model_settings["max_tokens"] = max_tokens
    if effort := model_config.get("reasoning_effort"):
        model_settings["openai_reasoning_effort"] = effort
    agent: Agent[AssistantDeps, str] = Agent(
        model,
        output_type=str,
        instructions=SYSTEM_INSTRUCTIONS,
        deps_type=AssistantDeps,
        retries=MODEL_RETRIES,
        model_settings=model_settings,
    )
    register_tools(agent)
    return agent
