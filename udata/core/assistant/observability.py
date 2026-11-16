"""Langfuse tracing for the AI assistant.

pydantic-ai emits OpenTelemetry spans for agent runs, model requests and
tool calls; Langfuse exports them. Tracing is enabled only when the
``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY`` and ``LANGFUSE_BASE_URL``
settings are all set: every traced turn includes its full content.

The tracer provider is private to the assistant, so enabling tracing never
changes the process-wide OpenTelemetry provider. It is created lazily, on
the first chat turn of each worker process, after any fork.
"""

import logging
import threading
from contextlib import contextmanager
from contextvars import ContextVar

from flask import current_app
from langfuse import Langfuse, LangfuseOtelSpanAttributes, propagate_attributes
from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from pydantic_ai import Agent
from pydantic_ai.models.instrumented import InstrumentationSettings

from udata.core.assistant.prompts import PROMPT_VERSION

log = logging.getLogger(__name__)

TRACE_NAME = "assistant-chat"
TURN_SUMMARY_NAME = "turn-summary"

_lock = threading.Lock()
_initialized = False
_client: Langfuse | None = None

# W3C trace context and baggage, explicitly: the process-wide propagator is
# left alone, like the process-wide tracer provider.
_PARENT_PROPAGATOR = CompositePropagator([TraceContextTextMapPropagator(), W3CBaggagePropagator()])

# Per-turn record of the turn's first span (the ``agent run`` root). Tasks
# and tool threads of the turn copy the context, so they share this dict.
_turn: ContextVar[dict[str, str] | None] = ContextVar("assistant_turn", default=None)


class _TurnRecorder(SpanProcessor):
    """Remember the trace and span ids of the first span started in a turn."""

    def on_start(self, span, parent_context=None) -> None:
        turn = _turn.get()
        if turn is not None and "trace_id" not in turn:
            span_context = span.get_span_context()
            turn["trace_id"] = otel_trace.format_trace_id(span_context.trace_id)
            turn["span_id"] = otel_trace.format_span_id(span_context.span_id)


def init_tracing() -> Langfuse | None:
    """Start tracing once per process when Langfuse is configured.

    Returns the Langfuse client, or None when tracing is disabled.
    """
    global _initialized, _client
    if _initialized:
        return _client
    with _lock:
        if _initialized:
            return _client
        config = current_app.config
        public_key = config.get("LANGFUSE_PUBLIC_KEY")
        secret_key = config.get("LANGFUSE_SECRET_KEY")
        base_url = config.get("LANGFUSE_BASE_URL")
        if public_key and secret_key and base_url:
            provider = TracerProvider()
            provider.add_span_processor(_TurnRecorder())
            _client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                base_url=base_url,
                tracer_provider=provider,
            )
            Agent.instrument_all(InstrumentationSettings(tracer_provider=provider))
            log.info("Assistant tracing enabled (Langfuse at %s)", base_url)
        elif public_key or secret_key or base_url:
            # The SDK would fall back to Langfuse Cloud without a base URL:
            # never send conversations anywhere unless all three are set.
            log.warning(
                "Assistant tracing disabled: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY "
                "and LANGFUSE_BASE_URL must all be set"
            )
        _initialized = True
        return _client


def extract_parent(headers) -> otel_context.Context | None:
    """Context of the caller's span, from its ``traceparent`` and ``baggage`` headers.

    Only when tracing is on and ``AI_TRACE_ACCEPT_PARENT`` is set: otherwise any
    client could graft its turns into arbitrary traces. ``langfuse_*`` baggage
    entries are copied onto the turn's spans by the Langfuse span processor,
    but the turn's own attributes (trace name, session, version) override them.
    """
    if _client is None or not current_app.config.get("AI_TRACE_ACCEPT_PARENT"):
        return None
    return _PARENT_PROPAGATOR.extract(carrier=headers)


@contextmanager
def trace_turn(
    *,
    session_id: str | None,
    metadata: dict[str, str],
    tags: list[str] | None = None,
    parent: otel_context.Context | None = None,
):
    """Group one chat turn's spans under shared attributes.

    The session is the chat ``id`` sent by the client, so every turn of a
    conversation lands in one Langfuse session. With a ``parent`` (see
    ``extract_parent``), the turn joins the caller's trace. A no-op when
    tracing is off.
    """
    if _client is None:
        yield
        return
    parent_token = otel_context.attach(parent) if parent is not None else None
    turn_token = _turn.set({})
    try:
        with propagate_attributes(
            trace_name=TRACE_NAME,
            session_id=session_id,
            version=PROMPT_VERSION,
            metadata=metadata,
            tags=tags or None,
        ):
            yield
    finally:
        _turn.reset(turn_token)
        if parent_token is not None:
            otel_context.detach(parent_token)


def turn_trace_id() -> str | None:
    """Trace id of the current turn, once its first span has started."""
    turn = _turn.get()
    return turn.get("trace_id") if turn else None


def record_turn_end(*, tool_count: int, sql_count: int) -> None:
    """Record the turn's budget use, only known once the run is over.

    Emitted as a ``turn-summary`` event under the turn's root span, with the
    counts also propagated as trace metadata.
    """
    turn = _turn.get()
    if _client is None or not turn or "trace_id" not in turn:
        return
    counts = {"tool_count": str(tool_count), "sql_count": str(sql_count)} # TODO: verify if that is still up-to-date with the current tools
    root = otel_trace.NonRecordingSpan(
        otel_trace.SpanContext(
            trace_id=int(turn["trace_id"], 16),
            span_id=int(turn["span_id"], 16),
            is_remote=False,
            trace_flags=otel_trace.TraceFlags(otel_trace.TraceFlags.SAMPLED),
        )
    )
    # Not ``create_event(trace_context=...)``: it would flag the event as the
    # trace root. Parenting through the current context keeps ``agent run`` root.
    with otel_trace.use_span(root), propagate_attributes(metadata=counts):
        _client.create_event(name=TURN_SUMMARY_NAME, metadata=counts)


def mark_tool_warning(message: str) -> None:
    """Flag the current tool span as a WARNING (refused or failed tool call)."""
    span = otel_trace.get_current_span()
    if span.is_recording():
        span.set_attribute(LangfuseOtelSpanAttributes.OBSERVATION_LEVEL, "WARNING")
        span.set_attribute(LangfuseOtelSpanAttributes.OBSERVATION_STATUS_MESSAGE, message)


def reset_tracing() -> None:
    """Forget the tracing state (tests only): the next turn re-reads the settings."""
    global _initialized, _client
    with _lock:
        if _client is not None:
            _client.shutdown()
        _client = None
        _initialized = False
        Agent.instrument_all(False)
