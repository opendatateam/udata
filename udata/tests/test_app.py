from contextvars import Context

import pytest
from flask import request
from werkzeug.exceptions import BadRequest

from udata.core.assistant.api import AssistantChatAPI
from udata.tests.api import PytestOnlyAPITestCase

CHAT_URL = "/api/1/assistant/chat/"


class UDataRequestTest(PytestOnlyAPITestCase):
    def test_max_content_length_follows_the_routed_view_class(self):
        with self.app.test_request_context(CHAT_URL, method="POST"):
            assert request.max_content_length == AssistantChatAPI.max_content_length

    @pytest.mark.options(MAX_CONTENT_LENGTH=1234)
    def test_max_content_length_defaults_to_the_config_on_other_views(self):
        with self.app.test_request_context("/api/1/datasets/", method="POST"):
            assert request.max_content_length == 1234

    def test_max_content_length_outside_an_app_context_falls_back_to_werkzeug(self):
        context = self.app.test_request_context(CHAT_URL, method="POST")
        context.push()
        current = request._get_current_object()
        context.pop()
        assert current.url_rule is not None
        # The test fixture keeps an app context open: read from an empty context.
        assert Context().run(lambda: current.max_content_length) is None

    def test_an_explicit_none_restores_the_app_default(self):
        with self.app.test_request_context(CHAT_URL, method="POST"):
            request.max_content_length = None
            assert request.max_content_length is None

    def test_an_explicit_value_overrides_the_view_class_limit(self):
        with self.app.test_request_context(CHAT_URL, method="POST"):
            request.max_content_length = 10
            assert request.max_content_length == 10


class UdataJsonProviderTest(PytestOnlyAPITestCase):
    def test_too_deeply_nested_json_is_invalid_json(self):
        body = "[" * 300_000
        with self.app.test_request_context(
            method="POST", data=body, content_type="application/json"
        ):
            assert request.get_json(silent=True) is None
            with pytest.raises(BadRequest):
                request.get_json()
