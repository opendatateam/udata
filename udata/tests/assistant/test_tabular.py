import pytest
import requests

from udata.core.assistant.tabular import TabularClient, TabularError
from udata.tests import PytestOnlyTestCase

BASE_URL = "https://tabular.example.com"
RESOURCE_ID = "5c4ae7a0e3f14a3f8b1d2e9f"


class TabularClientTest(PytestOnlyTestCase):
    def setup_method(self, method):
        self.app.config["TABULAR_SQL_URL"] = BASE_URL
        self.app.config["TABULAR_SQL_TIMEOUT"] = 7

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

    def test_http_error_raises_tabular_error(self, requests_mock):
        requests_mock.post(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/sql",
            status_code=500,
            json={"error": "boom"},
        )
        with pytest.raises(TabularError):
            self.make_client().execute_sql(RESOURCE_ID, "SELECT 1")

    def test_timeout_raises_tabular_error(self, requests_mock):
        requests_mock.post(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/sql",
            exc=requests.exceptions.ConnectTimeout,
        )
        with pytest.raises(TabularError):
            self.make_client().execute_sql(RESOURCE_ID, "SELECT 1")

    def test_invalid_json_raises_tabular_error(self, requests_mock):
        requests_mock.post(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/sql",
            text="not json",
        )
        with pytest.raises(TabularError):
            self.make_client().execute_sql(RESOURCE_ID, "SELECT 1")

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

    def test_none_timeout_falls_back_to_bounded_default(self, requests_mock):
        self.app.config["TABULAR_SQL_TIMEOUT"] = None
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/",
            json={"ok": True},
        )
        client = self.make_client()
        assert client.get_profile(RESOURCE_ID) == {"ok": True}
        assert requests_mock.request_history[0].timeout == 30

    def test_non_positive_timeout_falls_back_to_bounded_default(self, requests_mock):
        self.app.config["TABULAR_SQL_TIMEOUT"] = 0
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/",
            json={"ok": True},
        )
        client = self.make_client(timeout=-1)
        assert client.get_profile(RESOURCE_ID) == {"ok": True}
        assert requests_mock.request_history[0].timeout == 30
