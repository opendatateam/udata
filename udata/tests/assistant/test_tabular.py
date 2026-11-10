import pytest
import requests

from udata.core.assistant.tabular import (
    TABULAR_TIMEOUT,
    TabularClient,
    TabularError,
    TabularRequestRefused,
)
from udata.tests import PytestOnlyTestCase

BASE_URL = "https://tabular.example.com"
RESOURCE_ID = "5c4ae7a0-e3f1-4a3f-8b1d-2e9f00000000"


class TabularClientTest(PytestOnlyTestCase):
    def setup_method(self, method):
        self.app.config["TABULAR_API_URL"] = BASE_URL

    def make_client(self, **kwargs) -> TabularClient:
        with self.app.test_request_context():
            return TabularClient(**kwargs)

    def test_get_profile_returns_json(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/",
            json={"profile": {"a": "int"}},
        )
        assert self.make_client().get_profile(RESOURCE_ID) == {"profile": {"a": "int"}}

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
            client.get_data(bad_id, "a__groupby")
        assert not requests_mock.request_history

    def test_uuid_with_uppercase_and_braces_is_normalized(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/",
            json={"ok": True},
        )
        braced = "{5C4AE7A0-E3F1-4A3F-8B1D-2E9F00000000}"
        assert self.make_client().get_profile(braced) == {"ok": True}

    def test_http_error_raises_sanitized_tabular_error(self, requests_mock, caplog):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/?a__groupby",
            status_code=500,
            json={"error": "boom"},
        )
        with (
            self.app.test_request_context(),
            caplog.at_level("WARNING", logger="udata.core.assistant.tabular"),
        ):
            with pytest.raises(TabularError) as excinfo:
                self.make_client().get_data(RESOURCE_ID, "a__groupby")
        # The client-facing error is sanitized: no URL, no upstream details.
        message = str(excinfo.value)
        assert BASE_URL not in message
        assert "boom" not in message
        assert "500" not in message
        # The details stay in the server logs.
        assert any(BASE_URL in record.getMessage() for record in caplog.records)

    def test_refused_query_keeps_the_detail_for_the_agent(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/?a__groupby",
            status_code=400,
            json={
                "errors": [{"code": None, "title": "Invalid query", "detail": "Unknown column: x"}]
            },
        )
        with pytest.raises(TabularRequestRefused) as excinfo:
            self.make_client().get_data(RESOURCE_ID, "a__groupby")
        assert excinfo.value.detail == "Unknown column: x"
        assert BASE_URL not in str(excinfo.value)

    def test_bad_request_without_detail_is_a_generic_error(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/?a__groupby", status_code=400, text="nope"
        )
        with pytest.raises(TabularError) as excinfo:
            self.make_client().get_data(RESOURCE_ID, "a__groupby")
        assert not isinstance(excinfo.value, TabularRequestRefused)

    def test_missing_resource_says_it_is_not_available(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/?a__groupby",
            status_code=404,
            json={"errors": [{"detail": "not found"}]},
        )
        with pytest.raises(TabularError, match="pas disponible"):
            self.make_client().get_data(RESOURCE_ID, "a__groupby")

    def test_timeout_raises_sanitized_tabular_error(self, requests_mock, caplog):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/?a__groupby",
            exc=requests.exceptions.ConnectTimeout,
        )
        with (
            self.app.test_request_context(),
            caplog.at_level("WARNING", logger="udata.core.assistant.tabular"),
        ):
            with pytest.raises(TabularError) as excinfo:
                self.make_client().get_data(RESOURCE_ID, "a__groupby")
        assert BASE_URL not in str(excinfo.value)
        assert any(BASE_URL in record.getMessage() for record in caplog.records)

    def test_invalid_json_raises_sanitized_tabular_error(self, requests_mock, caplog):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/?a__groupby",
            text="not json",
        )
        with (
            self.app.test_request_context(),
            caplog.at_level("WARNING", logger="udata.core.assistant.tabular"),
        ):
            with pytest.raises(TabularError) as excinfo:
                self.make_client().get_data(RESOURCE_ID, "a__groupby")
        assert "not json" not in str(excinfo.value)
        # The server-side log keeps the diagnostic details (URL, error).
        assert any(BASE_URL in record.getMessage() for record in caplog.records)

    def test_unconfigured_raises_tabular_error(self):
        self.app.config["TABULAR_API_URL"] = None
        client = self.make_client()
        with pytest.raises(TabularError):
            client.get_profile(RESOURCE_ID)
        with pytest.raises(TabularError):
            client.get_data(RESOURCE_ID, "a__groupby")

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
        assert requests_mock.request_history[0].timeout == TABULAR_TIMEOUT

    def test_non_positive_timeout_falls_back_to_bounded_default(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/",
            json={"ok": True},
        )
        client = self.make_client(timeout=-1)
        assert client.get_profile(RESOURCE_ID) == {"ok": True}
        assert requests_mock.request_history[0].timeout == TABULAR_TIMEOUT

    def test_get_data_returns_json(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/",
            json={"data": [{"a": 1}], "links": {}},
        )
        assert self.make_client().get_data(RESOURCE_ID, "a__groupby") == {
            "data": [{"a": 1}],
            "links": {},
        }

    def test_get_data_sends_the_query_string_verbatim(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/", json={"data": [], "links": {}}
        )
        self.make_client().get_data(
            RESOURCE_ID, "a__groupby&b__sum&page=1&page_size=50&c__exact=x%252Ey"
        )
        assert requests_mock.request_history[0].url.endswith(
            "?a__groupby&b__sum&page=1&page_size=50&c__exact=x%252Ey"
        )

    def test_has_more_groups_is_true_when_the_51st_group_exists(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/", json={"data": [{"a": "x"}]}
        )
        assert self.make_client().has_more_groups(RESOURCE_ID, "a__groupby&b__sum") is True
        assert requests_mock.request_history[0].url.endswith(
            "?a__groupby&b__sum&page=51&page_size=1"
        )

    def test_has_more_groups_is_false_on_an_empty_51st_page(self, requests_mock):
        requests_mock.get(f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/", json={"data": []})
        assert self.make_client().has_more_groups(RESOURCE_ID, "a__groupby") is False

    def test_has_more_groups_with_an_empty_query(self, requests_mock):
        requests_mock.get(f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/", json={"data": []})
        self.make_client().has_more_groups(RESOURCE_ID, "")
        assert requests_mock.request_history[0].url.endswith("/data/?page=51&page_size=1")
