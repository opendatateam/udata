from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from udata.core.assistant import history
from udata.core.assistant.history import CLEARED_TOOL_RESULT, compact_history


def exchange(index: int, result: str = "rows") -> list:
    """A question, a tool call and its result, then the answer."""
    call_id = f"call-{index}"
    return [
        ModelRequest(parts=[UserPromptPart(content=f"question {index}")], instructions="prompt"),
        ModelResponse(parts=[ToolCallPart(tool_name="query_data", args={}, tool_call_id=call_id)]),
        ModelRequest(
            parts=[ToolReturnPart(tool_name="query_data", content=result, tool_call_id=call_id)]
        ),
        ModelResponse(parts=[TextPart(content=f"answer {index}")]),
    ]


def results(messages) -> list:
    return [
        part.content
        for message in messages
        for part in message.parts
        if isinstance(part, ToolReturnPart)
    ]


def test_all_the_text_is_kept():
    messages = [m for index in range(10) for m in exchange(index)]
    text = str(compact_history(messages, None))
    assert all(f"question {i}" in text and f"answer {i}" in text for i in range(10))


def test_only_the_recent_tool_results_are_kept():
    messages = [m for index in range(5) for m in exchange(index, result=f"rows {index}")]
    compacted = compact_history(messages, None)
    assert results(compacted) == [CLEARED_TOOL_RESULT] * 2 + ["rows 2", "rows 3", "rows 4"]
    # The calls stay, each with its result: providers refuse a call without one.
    assert sum(isinstance(p, ToolCallPart) for m in compacted for p in m.parts) == 5


def test_the_context_and_the_instructions_are_not_kept():
    messages = exchange(0)
    messages[0] = ModelRequest(
        parts=[UserPromptPart(content="<context>"), UserPromptPart(content="question 0")],
        instructions="prompt",
    )
    compacted = compact_history(messages, "<context>")
    assert [part.content for part in compacted[0].parts] == ["question 0"]
    assert all(m.instructions is None for m in compacted if isinstance(m, ModelRequest))


def test_the_oldest_exchanges_go_beyond_the_size_bound(monkeypatch):
    monkeypatch.setattr(history, "MAX_HISTORY_BYTES", 6_000)
    messages = [m for index in range(20) for m in exchange(index)]
    compacted = compact_history(messages, None)
    text = str(compacted)
    assert "question 19" in text
    assert "question 0" not in text
    assert isinstance(compacted[0], ModelRequest)
    assert isinstance(compacted[0].parts[0], UserPromptPart)


def test_a_last_exchange_beyond_the_size_bound_is_kept(monkeypatch):
    monkeypatch.setattr(history, "MAX_HISTORY_BYTES", 10)
    compacted = compact_history([*exchange(0), *exchange(1)], None)
    assert "question 1" in str(compacted)
    assert "question 0" not in str(compacted)
