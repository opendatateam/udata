import time

import pytest
from flask import current_app, url_for

from udata.core.user.factories import UserFactory
from udata.tests.api import PytestOnlyAPITestCase

CDATA = "http://cdata.test"
TWO_DAYS_AGO = int(time.time()) - 2 * 24 * 3600
TWO_DAYS_LATER = int(time.time()) + 2 * 24 * 3600


# The session cookie must carry the OAuth state from the login redirect to the callback:
# the test client speaks plain http to local.test, whatever a local udata.cfg says.
@pytest.mark.options(SESSION_COOKIE_SECURE=False, SESSION_COOKIE_DOMAIN=None, CDATA_BASE_URL=CDATA)
@pytest.mark.usefixtures("proconnect")
class ProConnectAuthTest(PytestOnlyAPITestCase):
    def get(self, url, *args, **kwargs):
        # pytest-flask keeps one app context, hence one `g`, for the whole test, and
        # flask-login caches the user there: the session cookie, which carries the
        # freshness, would never be read again. A context per request reads it.
        with current_app.app_context():
            return super().get(url, *args, **kwargs)

    def round_trip(self, proconnect, **query):
        response = self.get(url_for("api.proconnect_login", **query))
        assert response.status_code == 302
        callback = proconnect.authorize(response.location)
        return self.get(url_for("api.proconnect_auth", **callback))

    def sign_in(self, proconnect, email, authenticated_at=None):
        proconnect.agent_has_session(email, authenticated_at=authenticated_at)
        return self.round_trip(proconnect)

    def reauthenticate(self, proconnect):
        return self.round_trip(proconnect, reauth=1)

    def is_fresh(self) -> bool:
        """Whether a sensitive operation (here, changing the 2FA) goes through without a reauthentication."""
        response = self.get(
            url_for("security.two_factor_setup"), headers={"Accept": "application/json"}
        )
        if response.status_code == 401:
            assert response.json["response"]["reauth_required"]
            return False
        self.assert200(response)
        return True

    def assert_logged_in_as(self, user):
        response = self.get(url_for("api.me"))
        self.assert200(response)
        assert response.json["id"] == str(user.id)

    def test_login_from_a_fresh_proconnect_authentication_is_fresh(self, proconnect):
        UserFactory(email="jane@example.org")

        self.sign_in(proconnect, "jane@example.org")

        assert self.is_fresh()

    def test_login_from_an_old_proconnect_session_is_not_fresh(self, proconnect):
        user = UserFactory(email="jane@example.org")

        response = self.sign_in(proconnect, "jane@example.org", authenticated_at=TWO_DAYS_AGO)

        assert "flash=connected" in response.location
        self.assert_logged_in_as(user)
        assert not self.is_fresh()

    def test_login_with_an_auth_time_in_the_future_is_dated_now(self, proconnect):
        # flask-security would hold a date this far ahead as stale, a nearer one as fresh
        # for longer than `SECURITY_FRESHNESS`: either way, ProConnect's clock is not ours.
        UserFactory(email="jane@example.org")

        self.sign_in(proconnect, "jane@example.org", authenticated_at=TWO_DAYS_LATER)

        assert self.is_fresh()

    def test_login_without_auth_time_is_dated_at_the_login(self, proconnect):
        UserFactory(email="jane@example.org")
        proconnect.returns_auth_time = False

        self.sign_in(proconnect, "jane@example.org")

        assert self.is_fresh()

    def test_reauthentication_makes_the_session_fresh(self, proconnect):
        user = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org", authenticated_at=TWO_DAYS_AGO)

        response = self.reauthenticate(proconnect)

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_success"
        self.assert_logged_in_as(user)
        assert self.is_fresh()

    def test_reauthentication_answered_by_the_open_session_is_refused(self, proconnect):
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org", authenticated_at=TWO_DAYS_AGO)
        proconnect.honors_max_age = False

        response = self.reauthenticate(proconnect)

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_failed"
        assert not self.is_fresh()

    def test_reauthentication_without_auth_time_is_refused(self, proconnect):
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org", authenticated_at=TWO_DAYS_AGO)
        proconnect.returns_auth_time = False

        response = self.reauthenticate(proconnect)

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_failed"
        assert not self.is_fresh()

    def test_reauthentication_cancelled_at_proconnect_is_refused(self, proconnect):
        user = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org", authenticated_at=TWO_DAYS_AGO)

        response = self.get(url_for("api.proconnect_login", reauth=1))
        response = self.get(url_for("api.proconnect_auth", **proconnect.deny(response.location)))

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_failed"
        self.assert_logged_in_as(user)
        assert not self.is_fresh()

    def test_reauthentication_after_logging_out_is_refused(self, proconnect):
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org", authenticated_at=TWO_DAYS_AGO)
        response = self.get(url_for("api.proconnect_login", reauth=1))
        self.get(url_for("security.logout"))

        callback = proconnect.authorize(response.location)
        response = self.get(url_for("api.proconnect_auth", **callback))

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_failed"
        self.assert401(self.get(url_for("api.me")))

    def test_reauthentication_as_someone_else_is_refused(self, proconnect):
        user = UserFactory(email="jane@example.org")
        UserFactory(email="john@example.org")
        self.sign_in(proconnect, "jane@example.org", authenticated_at=TWO_DAYS_AGO)
        proconnect.agent_has_session("john@example.org")

        response = self.reauthenticate(proconnect)

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_identity_mismatch"
        self.assert_logged_in_as(user)
        assert not self.is_fresh()

    def test_reauthentication_requires_being_logged_in(self):
        self.assert401(self.get(url_for("api.proconnect_login", reauth=1)))

    def test_abandoned_reauthentication_does_not_apply_to_the_next_login(self, proconnect):
        UserFactory(email="jane@example.org")
        john = UserFactory(email="john@example.org")
        self.sign_in(proconnect, "jane@example.org", authenticated_at=TWO_DAYS_AGO)
        self.get(url_for("api.proconnect_login", reauth=1))

        response = self.sign_in(proconnect, "john@example.org")

        assert "flash=connected" in response.location
        self.assert_logged_in_as(john)
