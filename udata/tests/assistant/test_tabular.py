import pytest
import requests

from udata.core.assistant.data_query import PAGE_SIZE
from udata.core.assistant.tabular import (
    MAX_DETAIL_LENGTH,
    TABULAR_TIMEOUT,
    TabularClient,
    TabularError,
    TabularRequestRefused,
    has_more_rows,
)
from udata.tests import PytestOnlyTestCase

BASE_URL = "https://tabular.example.com"
RESOURCE_ID = "5c4ae7a0-e3f1-4a3f-8b1d-2e9f00000000"


class TabularClientTest(PytestOnlyTestCase):
    def setup_method(self, method):
        self.app.config["TABULAR_API_URL"] = BASE_URL

    def test_a_trailing_slash_in_the_base_url_does_not_double(self, requests_mock):
        self.app.config["TABULAR_API_URL"] = f"{BASE_URL}/"
        requests_mock.get(f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/", json={})
        TabularClient().get_profile(RESOURCE_ID)
        assert requests_mock.request_history[0].url.startswith(f"{BASE_URL}/api/")

    def test_get_profile_returns_json_within_the_timeout(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/",
            json={"profile": {"a": "int"}},
        )
        assert TabularClient().get_profile(RESOURCE_ID) == {"profile": {"a": "int"}}
        assert requests_mock.request_history[0].timeout == TABULAR_TIMEOUT

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
        client = TabularClient()
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
        assert TabularClient().get_profile(braced) == {"ok": True}

    def refused(self, requests_mock, status, **body) -> TabularRequestRefused:
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/?a__groupby", status_code=status, **body
        )
        with pytest.raises(TabularRequestRefused) as excinfo:
            TabularClient().get_data(RESOURCE_ID, "a__groupby")
        return excinfo.value

    @staticmethod
    def error(detail, title="Invalid query") -> dict:
        return {"json": {"errors": [{"code": None, "title": title, "detail": detail}]}}

    def test_an_error_status_relays_the_detail(self, requests_mock):
        refusal = self.refused(requests_mock, 400, **self.error("Unknown column: x"))
        assert (refusal.status, refusal.detail) == (400, "Unknown column: x")

    def test_an_error_relays_the_message_of_a_database_error(self, requests_mock):
        # api-tabular relays PostgREST's error object as is, internal table name included.
        message = 'relation "csvapi.0123456789abcdef0123456789abcdef" does not exist'
        detail = {"code": "42P01", "details": None, "hint": None, "message": message}
        refusal = self.refused(requests_mock, 404, **self.error(detail, "Database error"))
        assert (refusal.status, refusal.detail) == (404, message)

    def test_an_unauthorized_parameter_is_relayed_as_is(self, requests_mock):
        detail = "score is not among the allowed columns: {'birth', 'id'}"
        refusal = self.refused(
            requests_mock, 403, **self.error(detail, title="Unauthorized parameters")
        )
        assert (refusal.status, refusal.detail) == (403, detail)

    def test_an_error_without_detail_gives_its_title(self, requests_mock):
        refusal = self.refused(requests_mock, 400, **self.error(None, title="Invalid query"))
        assert refusal.detail == "Invalid query"

    def test_a_plain_text_error_gives_its_body(self, requests_mock):
        # api-tabular's own 404, in plain text, for a resource it does not know
        refusal = self.refused(requests_mock, 404, text="404: Not Found")
        assert (refusal.status, refusal.detail) == (404, "404: Not Found")

    def test_the_detail_is_bounded(self, requests_mock):
        refusal = self.refused(requests_mock, 400, **self.error("x" * 1000))
        assert len(refusal.detail) == MAX_DETAIL_LENGTH

    def test_the_url_stays_in_the_logs(self, requests_mock, caplog):
        with caplog.at_level("WARNING", logger="udata.core.assistant.tabular"):
            refusal = self.refused(requests_mock, 500, json={"error": "boom"})
        assert BASE_URL not in str(refusal)
        assert any(BASE_URL in record.getMessage() for record in caplog.records)

    def test_timeout_raises_sanitized_tabular_error(self, requests_mock, caplog):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/?a__groupby",
            exc=requests.exceptions.ConnectTimeout,
        )
        with (
            caplog.at_level("WARNING", logger="udata.core.assistant.tabular"),
            pytest.raises(TabularError) as excinfo,
        ):
            TabularClient().get_data(RESOURCE_ID, "a__groupby")
        assert BASE_URL not in str(excinfo.value)
        assert any(BASE_URL in record.getMessage() for record in caplog.records)

    def test_invalid_json_raises_sanitized_tabular_error(self, requests_mock, caplog):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/?a__groupby",
            text="not json",
        )
        with (
            caplog.at_level("WARNING", logger="udata.core.assistant.tabular"),
            pytest.raises(TabularError) as excinfo,
        ):
            TabularClient().get_data(RESOURCE_ID, "a__groupby")
        assert "not json" not in str(excinfo.value)
        # The server-side log keeps the diagnostic details (URL, error).
        assert any(
            BASE_URL in record.getMessage() and "Expecting value" in record.getMessage()
            for record in caplog.records
        )

    def test_unconfigured_raises_tabular_error(self, caplog):
        self.app.config["TABULAR_API_URL"] = None
        client = TabularClient()
        with caplog.at_level("WARNING", logger="udata.core.assistant.tabular"):
            with pytest.raises(TabularError):
                client.get_profile(RESOURCE_ID)
            with pytest.raises(TabularError):
                client.get_data(RESOURCE_ID, "a__groupby")
        # A misconfigured deployment leaves a trace in the logs.
        assert any("TABULAR_API_URL" in record.getMessage() for record in caplog.records)

    def test_get_data_sends_the_query_string_verbatim(self, requests_mock):
        requests_mock.get(
            f"{BASE_URL}/api/resources/{RESOURCE_ID}/data/", json={"data": [{"a": 1}], "links": {}}
        )
        result = TabularClient().get_data(
            RESOURCE_ID, "a__groupby&b__sum&page=1&page_size=50&c__exact=x%252Ey"
        )
        assert result == {"data": [{"a": 1}], "links": {}}
        assert requests_mock.request_history[0].url.endswith(
            "?a__groupby&b__sum&page=1&page_size=50&c__exact=x%252Ey"
        )

    def full_page(self, **page):
        """A first page of PAGE_SIZE rows, with these extra response fields."""
        return {"data": [{"a": i} for i in range(PAGE_SIZE)], **page}

    NEXT = {"next": "https://tabular.example.com/next"}

    def test_has_more_rows_is_false_on_a_partial_page(self):
        assert has_more_rows({"data": [{"a": 1}] * (PAGE_SIZE - 1), "links": self.NEXT}) is False

    @pytest.mark.parametrize("total,expected", [(926, True), (51, True), (50, False)])
    def test_has_more_rows_reads_the_exact_total_of_a_raw_query(self, total, expected):
        assert has_more_rows(self.full_page(links=self.NEXT, meta={"total": total})) is expected

    @pytest.mark.parametrize("links", [{"next": None}, {}, None])
    def test_has_more_rows_is_false_on_a_full_page_without_next_link(self, links):
        # api-tabular links an aggregated page to the next one only when it has rows
        assert has_more_rows(self.full_page(links=links)) is False

    def test_has_more_rows_follows_the_next_link_of_an_aggregated_page(self):
        assert has_more_rows(self.full_page(links=self.NEXT)) is True

    @pytest.mark.parametrize("page", [None, [], {"data": "rows"}])
    def test_has_more_rows_is_false_on_an_unexpected_page(self, page):
        assert has_more_rows(page) is False
