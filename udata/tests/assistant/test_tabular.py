from uuid import UUID

import pytest
import requests

from udata.core.assistant.data_query import PAGE_SIZE
from udata.core.assistant.tabular import (
    MAX_DETAIL_LENGTH,
    TABULAR_TIMEOUT,
    TabularClient,
    TabularError,
    TabularPage,
    TabularProfile,
    TabularRequestRefused,
    TabularUnexpectedAnswer,
    has_more_rows,
)
from udata.tests import PytestOnlyTestCase

BASE_URL = "https://tabular.example.com"
RESOURCE_ID = UUID("5c4ae7a0-e3f1-4a3f-8b1d-2e9f00000000")
PROFILE = {"profile": {"header": ["a"], "columns": {"a": {"python_type": "int"}}}}


class TabularClientTest(PytestOnlyTestCase):
    def setup_method(self, method):
        self.app.config["TABULAR_API_URL"] = BASE_URL

    def test_a_trailing_slash_in_the_base_url_does_not_double(self, requests_mock):
        self.app.config["TABULAR_API_URL"] = f"{BASE_URL}/"
        requests_mock.get(f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/", json=PROFILE)
        TabularClient().get_profile(RESOURCE_ID)
        assert requests_mock.request_history[0].url.startswith(f"{BASE_URL}/api/")

    def test_get_profile_reads_the_profile_within_the_timeout(self, requests_mock):
        requests_mock.get(f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/", json=PROFILE)
        profile = TabularClient().get_profile(RESOURCE_ID)
        assert profile == TabularProfile.model_validate(PROFILE)
        # csv-detective leaves total_lines out for large files.
        assert profile.profile.total_lines is None
        assert requests_mock.request_history[0].timeout == TABULAR_TIMEOUT

    def test_the_columns_of_a_profile_follow_the_header_order(self):
        profile = TabularProfile.model_validate(
            {
                "profile": {
                    "header": ["b", "a"],
                    "columns": {"a": {"python_type": "int"}, "b": {"python_type": "string"}},
                }
            }
        )
        assert list(profile.columns().items()) == [("b", "string"), ("a", "int")]

    def test_a_column_without_type_is_left_out_of_the_profile(self):
        profile = TabularProfile.model_validate(
            {"profile": {"columns": {"a": {"python_type": "int"}, "b": {}}}}
        )
        assert profile.columns() == {"a": "int"}

    @pytest.mark.parametrize("body", [{"text": '{"profile": "x"}'}, {"text": "not json"}])
    def test_an_unexpected_answer_raises_sanitized_tabular_error(self, requests_mock, caplog, body):
        requests_mock.get(f"{BASE_URL}/api/resources/{RESOURCE_ID}/profile/", **body)
        with (
            caplog.at_level("WARNING", logger="udata.core.assistant.tabular"),
            pytest.raises(TabularUnexpectedAnswer) as excinfo,
        ):
            TabularClient().get_profile(RESOURCE_ID)
        assert BASE_URL not in str(excinfo.value)
        assert body["text"] not in str(excinfo.value)
        assert any(BASE_URL in record.getMessage() for record in caplog.records)

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

    @pytest.mark.parametrize("status", [400, 403])
    def test_an_error_status_relays_the_detail(self, requests_mock, status):
        refusal = self.refused(requests_mock, status, **self.error("Unknown column: x"))
        assert (refusal.status, refusal.detail) == (status, "Unknown column: x")

    def test_an_error_relays_the_message_of_a_database_error(self, requests_mock):
        # api-tabular relays PostgREST's error object as is, internal table name included.
        message = 'relation "csvapi.0123456789abcdef0123456789abcdef" does not exist'
        detail = {"code": "42P01", "details": None, "hint": None, "message": message}
        refusal = self.refused(requests_mock, 404, **self.error(detail, "Database error"))
        assert (refusal.status, refusal.detail) == (404, message)

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
        assert result == TabularPage(data=[{"a": 1}])
        assert requests_mock.request_history[0].url.endswith(
            "?a__groupby&b__sum&page=1&page_size=50&c__exact=x%252Ey"
        )

    def full_page(self, **page):
        """A first page of PAGE_SIZE rows, with these extra response fields."""
        return TabularPage.model_validate({"data": [{"a": i} for i in range(PAGE_SIZE)], **page})

    NEXT = {"next": "https://tabular.example.com/next"}

    def test_has_more_rows_is_false_on_a_partial_page(self):
        page = TabularPage.model_validate(
            {"data": [{"a": 1}] * (PAGE_SIZE - 1), "links": self.NEXT}
        )
        assert has_more_rows(page) is False

    @pytest.mark.parametrize("total,expected", [(51, True), (50, False)])
    def test_has_more_rows_reads_the_exact_total_of_a_raw_query(self, total, expected):
        assert has_more_rows(self.full_page(links=self.NEXT, meta={"total": total})) is expected

    def test_has_more_rows_is_false_on_a_full_page_without_next_link(self):
        # api-tabular links an aggregated page to the next one only when it has rows
        assert has_more_rows(self.full_page()) is False

    def test_has_more_rows_follows_the_next_link_of_an_aggregated_page(self):
        assert has_more_rows(self.full_page(links=self.NEXT)) is True
