"""The conversation history the server keeps, compacted as the model reads it again."""

import dataclasses

from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ToolReturnPart,
    UserPromptPart,
)

# Exchanges whose tool results are kept whole: older ones keep the call, not the result.
KEPT_TOOL_RESULT_EXCHANGES = 3
# Bound on the stored history: the oldest exchanges go first.
MAX_HISTORY_BYTES = 512 * 1024

CLEARED_TOOL_RESULT = (
    "Result removed from the conversation history: call the tool again if you need it."
)


def _asks(message: ModelMessage) -> bool:
    """Whether the message is a user question, the start of an exchange."""
    return isinstance(message, ModelRequest) and any(
        isinstance(part, UserPromptPart) for part in message.parts
    )


def _without_context(message: ModelMessage, context: str | None) -> ModelMessage:
    """The request without the server context and the instructions, both rebuilt each turn."""
    if not isinstance(message, ModelRequest):
        return message
    parts = [
        part
        for part in message.parts
        if not (context and isinstance(part, UserPromptPart) and part.content == context)
    ]
    return dataclasses.replace(message, parts=parts, instructions=None)


def _without_tool_results(message: ModelMessage) -> ModelMessage:
    if not isinstance(message, ModelRequest):
        return message
    parts = [
        dataclasses.replace(part, content=CLEARED_TOOL_RESULT)
        if isinstance(part, ToolReturnPart)
        else part
        for part in message.parts
    ]
    return dataclasses.replace(message, parts=parts)


def _size(exchanges: list[list[ModelMessage]]) -> int:
    return len(ModelMessagesTypeAdapter.dump_json([m for exchange in exchanges for m in exchange]))


def compact_history(messages: list[ModelMessage], context: str | None) -> list[ModelMessage]:
    """The history to store: all the text, recent tool results only, within a size bound."""
    exchanges: list[list[ModelMessage]] = []
    for message in messages:
        if _asks(message) or not exchanges:
            exchanges.append([])
        exchanges[-1].append(_without_context(message, context))

    old = len(exchanges) - KEPT_TOOL_RESULT_EXCHANGES
    exchanges = [
        [_without_tool_results(m) for m in exchange] if index < old else exchange
        for index, exchange in enumerate(exchanges)
    ]
    while len(exchanges) > 1 and _size(exchanges) > MAX_HISTORY_BYTES:
        exchanges.pop(0)
    return [message for exchange in exchanges for message in exchange]
