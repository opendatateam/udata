import pytest

from udata.app import cache as cache_extension
from udata.core.assistant.limits import QuotaExceeded, check_and_consume_quota
from udata.tests import PytestOnlyTestCase


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
