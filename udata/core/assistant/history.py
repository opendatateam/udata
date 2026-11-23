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


def asks(message: ModelMessage) -> bool:
    """Whether the message is a user question, the start of an exchange."""
    return isinstance(message, ModelRequest) and any(
        isinstance(part, UserPromptPart) for part in message.parts
    )


def _compacted(message: ModelMessage, keep_tool_results: bool) -> ModelMessage:
    """The message without its instructions, rebuilt each turn, and maybe its tool results."""
    if not isinstance(message, ModelRequest):
        return message
    parts = message.parts
    if not keep_tool_results:
        parts = [
            dataclasses.replace(part, content=CLEARED_TOOL_RESULT)
            if isinstance(part, ToolReturnPart)
            else part
            for part in parts
        ]
    return dataclasses.replace(message, parts=parts, instructions=None)


def compact_history(messages: list[ModelMessage]) -> list[ModelMessage]:
    """The history to store: all the text, recent tool results only, within a size bound."""
    exchanges: list[list[ModelMessage]] = []
    for message in messages:
        if asks(message) or not exchanges:
            exchanges.append([])
        exchanges[-1].append(message)

    old = len(exchanges) - KEPT_TOOL_RESULT_EXCHANGES
    exchanges = [
        [_compacted(message, keep_tool_results=index >= old) for message in exchange]
        for index, exchange in enumerate(exchanges)
    ]
    sizes = [len(ModelMessagesTypeAdapter.dump_json(exchange)) for exchange in exchanges]
    while len(exchanges) > 1 and sum(sizes) > MAX_HISTORY_BYTES:
        exchanges.pop(0)
        sizes.pop(0)
    return [message for exchange in exchanges for message in exchange]
