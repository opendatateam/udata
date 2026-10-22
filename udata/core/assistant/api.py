"""SSE chat endpoint for the AI assistant.

Streams agent replies as Vercel AI protocol events (Server-Sent Events)
using pydantic-ai's UI adapter.
"""

import asyncio
import logging

from flask import Response, current_app, request, stream_with_context
from flask_login import current_user
from pydantic import ValidationError
from pydantic_ai import CancellationToken
from pydantic_ai.ui import SSE_CONTENT_TYPE
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.response_types import ErrorChunk

from udata.api import API, api
from udata.core.assistant.agent import get_agent
from udata.core.assistant.limits import QuotaExceeded, check_and_consume_quota
from udata.core.assistant.tabular import TabularClient
from udata.core.assistant.tools import AssistantDeps

log = logging.getLogger(__name__)

ns = api.namespace("assistant", "Assistant related operations")


@ns.route("/chat/", endpoint="assistant_chat")
class AssistantChatAPI(API):
    @api.secure
    @api.doc("assistant_chat")
    def post(self):
        """Stream an assistant reply as Vercel AI SSE events"""
        if not current_app.config["ASSISTANT_ENABLED"]:
            api.abort(404)

        if not current_app.config["ALBERT_API_KEY"]:
            return (
                {
                    "error": "L'assistant est activé mais la clé API Albert "
                    "(ALBERT_API_KEY) n'est pas configurée."
                },
                503,
            )

        # Client-submitted system messages are untrusted: the system prompt is
        # owned by the server, so strip them before building the run input.
        # Validation runs before the quota so a malformed body never consumes it.
        try:
            run_input = VercelAIAdapter.build_run_input(request.get_data())
        except ValidationError:
            api.abort(400, "Corps de requête invalide.")
        run_input.messages = [m for m in run_input.messages if m.role != "system"]

        try:
            check_and_consume_quota(str(current_user.id))
        except QuotaExceeded:
            api.abort(429, "Quota quotidien de l'assistant atteint.")

        agent = get_agent()
        adapter = VercelAIAdapter(agent, run_input, accept=SSE_CONTENT_TYPE)
        cancellation_token = CancellationToken()
        deps = AssistantDeps(tabular=TabularClient())

        stream = adapter.encode_stream(
            adapter.run_stream(
                deps=deps,
                cancellation_token=cancellation_token,
                timeout=current_app.config["ASSISTANT_TURN_TIMEOUT"],
            )
        )

        @stream_with_context
        def generate():
            # The adapter is async; drive it from a dedicated event loop inside
            # this sync generator so Flask streams chunk by chunk.
            loop = asyncio.new_event_loop()
            iterator = stream.__aiter__()
            try:
                while True:
                    try:
                        yield loop.run_until_complete(iterator.__anext__())
                    except StopAsyncIteration:
                        break
            except GeneratorExit:
                cancellation_token.cancel()
                raise
            except Exception as e:  # protocol-level error: the HTTP stream already started
                log.exception("Assistant chat stream failed")
                yield f"data: {ErrorChunk(error_text=str(e)).encode(adapter.sdk_version)}\n\n"
            finally:
                loop.close()

        return Response(
            generate(),
            content_type=SSE_CONTENT_TYPE,
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )
