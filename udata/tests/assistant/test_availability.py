"""The assistant disabled or misconfigured: its endpoint answers 503.

Apart from test_api.py, whose module options enable the assistant for every test.
"""

import json

import pytest
from flask import url_for

from udata.core.assistant.api import MAX_REQUEST_BYTES
from udata.tests.api import PytestOnlyAPITestCase

PAYLOAD = {
    "id": "chat-test",
    "trigger": "submit-message",
    "messages": [{"id": "msg-1", "role": "user", "parts": [{"type": "text", "text": "Bonjour"}]}],
}


class AssistantAvailabilityTest(PytestOnlyAPITestCase):
    def test_authentication_is_checked_first(self, mocker):
        agent = mocker.patch("udata.core.assistant.api.get_agent")
        assert self.post(url_for("api.assistant_chat"), data=PAYLOAD).status_code == 401
        agent.assert_not_called()

    def test_a_disabled_assistant_answers_503(self, mocker):
        agent = mocker.patch("udata.core.assistant.api.get_agent")
        self.login()
        assert self.post(url_for("api.assistant_chat"), data=PAYLOAD).status_code == 503
        agent.assert_not_called()

    @pytest.mark.options(AI_BASE_URL="http://albert.test/v1", AI_API_KEY=None)
    def test_a_missing_api_key_answers_503_and_is_logged(self, mocker, caplog):
        agent = mocker.patch("udata.core.assistant.api.get_agent")
        self.login()
        with caplog.at_level("ERROR", logger="udata.core.assistant.api"):
            response = self.post(url_for("api.assistant_chat"), data=PAYLOAD)
        assert response.status_code == 503
        # The setting name stays in the logs.
        assert "AI_API_KEY" not in response.json["message"]
        assert "AI_API_KEY" in caplog.text
        agent.assert_not_called()

    def test_a_disabled_assistant_is_checked_before_the_size_limit(self, mocker):
        agent = mocker.patch("udata.core.assistant.api.get_agent")
        self.login()
        body = json.dumps({**PAYLOAD, "pad": "x" * MAX_REQUEST_BYTES})
        response = self.client.post(
            url_for("api.assistant_chat"), data=body, content_type="application/json"
        )
        assert response.status_code == 503
        agent.assert_not_called()
