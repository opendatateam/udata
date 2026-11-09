import pytest
import requests

from udata.core.assistant.tabular import (
    DEFAULT_TIMEOUT,
    TABULAR_SQL_TIMEOUT,
    TabularClient,
    TabularError,
)
from udata.tests import PytestOnlyTestCase

BASE_URL = "https://tabular.example.com"
RESOURCE_ID = "5c4ae7a0-e3f1-4a3f-8b1d-2e9f00000000"


class TabularClientTest(PytestOnlyTestCase):
    def setup_method(self, method):
        self.app.config["TABULAR_SQL_URL"] = BASE_URL

    def make_client(self, **kwargs) -> TabularClient:
        with self.app.test_request_context():
            return TabularClient(**kwargs)

    def test_get_profile_returns_json(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/",
            json={"profile": {"a": "int"}},
        )
        assert self.make_client().get_profile(RESOURCE_ID) == {"profile": {"a": "int"}}

    def test_execute_sql_returns_columns_and_rows(self, requests_mock):
        requests_mock.post(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/sql",
            json={"columns": ["a"], "rows": [[1]]},
        )
        client = self.make_client()
        assert client.execute_sql(RESOURCE_ID, "SELECT a FROM data") == {
            "columns": ["a"],
            "rows": [[1]],
        }
        request = requests_mock.request_history[0]
        assert request.json() == {"query": "SELECT a FROM data"}

    @pytest.mark.parametrize(
        "bad_id",
        [
            "not-a-uuid",
            "../admin",
            "5c4ae7a0-e3f1-4a3f-8b1d-2e9f00000000/extra",
            "5c4ae7a0-e3f1-4a3f-8b1d-2e9f00000000?apikey=secret",
            "5c4ae7a0-e3f1-4a3f-8b1d-2e9f00000000#frag",
            "",
            None,
            42,
        ],
    )
    def test_malformed_resource_id_is_rejected_before_any_request(self, requests_mock, bad_id):
        """Only plain UUIDs may reach the upstream URL path."""
        client = self.make_client()
        with pytest.raises(TabularError):
            client.get_profile(bad_id)
        with pytest.raises(TabularError):
            client.execute_sql(bad_id, "SELECT 1")
        assert not requests_mock.request_history

    def test_uuid_with_uppercase_and_braces_is_normalized(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/",
            json={"ok": True},
        )
        braced = "{5C4AE7A0-E3F1-4A3F-8B1D-2E9F00000000}"
        assert self.make_client().get_profile(braced) == {"ok": True}

    def test_http_error_raises_sanitized_tabular_error(self, requests_mock, caplog):
        requests_mock.post(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/sql",
            status_code=500,
            json={"error": "boom"},
        )
        with (
            self.app.test_request_context(),
            caplog.at_level("WARNING", logger="udata.core.assistant.tabular"),
        ):
            with pytest.raises(TabularError) as excinfo:
                self.make_client().execute_sql(RESOURCE_ID, "SELECT 1")
        # The client-facing error is sanitized: no URL, no upstream details.
        message = str(excinfo.value)
        assert BASE_URL not in message
        assert "boom" not in message
        assert "500" not in message
        # The details stay in the server logs.
        assert any(BASE_URL in record.getMessage() for record in caplog.records)

    def test_timeout_raises_sanitized_tabular_error(self, requests_mock, caplog):
        requests_mock.post(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/sql",
            exc=requests.exceptions.ConnectTimeout,
        )
        with (
            self.app.test_request_context(),
            caplog.at_level("WARNING", logger="udata.core.assistant.tabular"),
        ):
            with pytest.raises(TabularError) as excinfo:
                self.make_client().execute_sql(RESOURCE_ID, "SELECT 1")
        assert BASE_URL not in str(excinfo.value)
        assert any(BASE_URL in record.getMessage() for record in caplog.records)

    def test_invalid_json_raises_sanitized_tabular_error(self, requests_mock, caplog):
        requests_mock.post(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/sql",
            text="not json",
        )
        with (
            self.app.test_request_context(),
            caplog.at_level("WARNING", logger="udata.core.assistant.tabular"),
        ):
            with pytest.raises(TabularError) as excinfo:
                self.make_client().execute_sql(RESOURCE_ID, "SELECT 1")
        assert "not json" not in str(excinfo.value)
        # The server-side log keeps the diagnostic details (URL, error).
        assert any(BASE_URL in record.getMessage() for record in caplog.records)

    def test_unconfigured_raises_tabular_error(self):
        self.app.config["TABULAR_SQL_URL"] = None
        client = self.make_client()
        with pytest.raises(TabularError):
            client.get_profile(RESOURCE_ID)
        with pytest.raises(TabularError):
            client.execute_sql(RESOURCE_ID, "SELECT 1")

    def test_explicit_overrides(self, requests_mock):
        requests_mock.get(
            f"https://override.example.com/api/resources/{RESOURCE_ID}/profile/",
            json={"ok": True},
        )
        client = self.make_client(base_url="https://override.example.com", timeout=3)
        assert client.get_profile(RESOURCE_ID) == {"ok": True}

    def test_default_timeout_comes_from_module_constant(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/",
            json={"ok": True},
        )
        client = self.make_client()
        assert client.get_profile(RESOURCE_ID) == {"ok": True}
        assert requests_mock.request_history[0].timeout == TABULAR_SQL_TIMEOUT

    def test_non_positive_timeout_falls_back_to_bounded_default(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/",
            json={"ok": True},
        )
        client = self.make_client(timeout=-1)
        assert client.get_profile(RESOURCE_ID) == {"ok": True}
        assert requests_mock.request_history[0].timeout == DEFAULT_TIMEOUT
