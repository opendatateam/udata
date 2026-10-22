import logging

import pytest

from udata.app import cache as cache_extension
from udata.core.assistant import limits
from udata.core.assistant.limits import QuotaExceeded, check_and_consume_quota
from udata.tests import PytestOnlyTestCase

LOG_PATH = "udata.core.assistant.limits"


class AssistantQuotaTest(PytestOnlyTestCase):
    def setup_method(self, method):
        self.app.config["CACHE_TYPE"] = "flask_caching.backends.SimpleCache"
        cache_extension.init_app(self.app)

    def test_20_calls_pass_and_21st_raises(self):
        with self.app.test_request_context():
            for _ in range(20):
                check_and_consume_quota("user-a")
            with pytest.raises(QuotaExceeded):
                check_and_consume_quota("user-a")

    def test_users_have_independent_counters(self):
        with self.app.test_request_context():
            for _ in range(20):
                check_and_consume_quota("user-a")
            # user-b is not affected by user-a having reached the quota
            check_and_consume_quota("user-b")
            for _ in range(19):
                check_and_consume_quota("user-b")
            with pytest.raises(QuotaExceeded):
                check_and_consume_quota("user-b")


class NullCacheFailOpenTest(PytestOnlyTestCase):
    def setup_method(self, method):
        # Explicitly keep the Testing default: NullCache (no-op backend).
        self.app.config["CACHE_TYPE"] = "flask_caching.backends.NullCache"
        cache_extension.init_app(self.app)

    def test_quota_is_a_noop_and_warns(self, monkeypatch, caplog):
        # The one-time warning is a module-level process flag: reset it so the
        # test is independent of test order.
        monkeypatch.setattr(limits, "_null_cache_warned", False)
        with self.app.test_request_context(), caplog.at_level(logging.WARNING, logger=LOG_PATH):
            for _ in range(25):
                check_and_consume_quota("user-a")  # beyond the quota of 20
        assert any(
            "quota" in record.message.lower() and "not enforced" in record.message.lower()
            for record in caplog.records
        )
