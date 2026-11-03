from datetime import datetime

import pytest
from flask import current_app, url_for

from udata.core.user.factories import UserFactory
from udata.tests.api import PytestOnlyAPITestCase

CDATA = "http://cdata.test"


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

    def post(self, url, *args, **kwargs):
        with current_app.app_context():
            return super().post(url, *args, **kwargs)

    def sign_in(self, proconnect, email):
        proconnect.agent_has_session(email)
        response = self.get(url_for("api.proconnect_login"))
        callback = proconnect.authorize(response.location)
        return self.get(url_for("api.proconnect_auth", **callback))

    def start_reauthentication(self, proconnect):
        """Go through the ProConnect sign-out, and return udata's redirection to the authorization."""
        response = self.get(url_for("api.proconnect_reauth"))
        signed_out = proconnect.end_session(response.location)
        return self.get(url_for("api.proconnect_logout", **signed_out))

    def reauthenticate(self, proconnect):
        response = self.start_reauthentication(proconnect)
        callback = proconnect.authorize(response.location)
        return self.get(url_for("api.proconnect_auth", **callback))

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

    def test_login_is_not_fresh(self, proconnect):
        # The open ProConnect session may have signed the agent in without asking anything.
        user = UserFactory(email="jane@example.org")

        response = self.sign_in(proconnect, "jane@example.org")

        assert "flash=connected" in response.location
        self.assert_logged_in_as(user)
        assert proconnect.authentications == 0
        assert not self.is_fresh()

    def test_login_completed_by_the_two_factor_is_fresh(self, proconnect):
        # A code from the agent's authenticator proves as much as a password on /verify.
        totp = current_app.extensions["security"].totp_factory
        secret = totp.generate_totp_secret()
        UserFactory(
            email="jane@example.org", tf_primary_method="authenticator", tf_totp_secret=secret
        )
        self.sign_in(proconnect, "jane@example.org")

        response = self.post(
            url_for("security.two_factor_token_validation"),
            {"code": totp.generate_totp_password(secret)},
        )

        self.assert200(response)
        assert self.is_fresh()

    @pytest.mark.options(SECURITY_TWO_FACTOR_REQUIRED=True)
    def test_login_sends_an_agent_without_2fa_to_the_cdata_setup_page(self, proconnect):
        UserFactory(email="jane@example.org")

        response = self.sign_in(proconnect, "jane@example.org")

        assert response.location == f"{CDATA}/setup-two-factor"
        self.assert401(self.get(url_for("api.me")))

    def test_login_sends_an_agent_with_2fa_to_the_cdata_validation_page(self, proconnect):
        UserFactory(
            email="jane@example.org",
            tf_primary_method="authenticator",
            tf_totp_secret="test_secret",
        )

        response = self.sign_in(proconnect, "jane@example.org")

        assert response.location == f"{CDATA}/tf-validate"
        self.assert401(self.get(url_for("api.me")))

    def test_reauthentication_makes_the_agent_authenticate_and_the_session_fresh(self, proconnect):
        user = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")

        response = self.reauthenticate(proconnect)

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_success"
        assert proconnect.authentications == 1
        self.assert_logged_in_as(user)
        assert self.is_fresh()

    def test_reauthentication_cancelled_at_proconnect_is_refused(self, proconnect):
        user = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")

        response = self.start_reauthentication(proconnect)
        response = self.get(url_for("api.proconnect_auth", **proconnect.deny(response.location)))

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_failed"
        self.assert_logged_in_as(user)
        assert not self.is_fresh()

    def test_reauthentication_can_be_retried_after_cancelling(self, proconnect):
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        response = self.start_reauthentication(proconnect)
        self.get(url_for("api.proconnect_auth", **proconnect.deny(response.location)))

        response = self.reauthenticate(proconnect)

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_success"
        assert self.is_fresh()

    def test_reauthentication_after_logging_out_is_refused(self, proconnect):
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        response = self.start_reauthentication(proconnect)
        self.get(url_for("security.logout"))

        callback = proconnect.authorize(response.location)
        response = self.get(url_for("api.proconnect_auth", **callback))

        assert response.location == f"{CDATA}/login"
        self.assert401(self.get(url_for("api.me")))

    def test_reauthentication_as_someone_else_is_refused(self, proconnect):
        user = UserFactory(email="jane@example.org")
        UserFactory(email="john@example.org")
        self.sign_in(proconnect, "jane@example.org")
        response = self.start_reauthentication(proconnect)
        proconnect.agent = "john@example.org"

        callback = proconnect.authorize(response.location)
        response = self.get(url_for("api.proconnect_auth", **callback))

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_identity_mismatch"
        self.assert_logged_in_as(user)
        assert not self.is_fresh()

    def test_reauthentication_requires_being_logged_in(self):
        # The cdata session expired on /verify: signing in again is what's left to do.
        response = self.get(url_for("api.proconnect_reauth"))

        assert response.location == f"{CDATA}/login"

    def test_reauthentication_requires_a_proconnect_login(self):
        # Signed in with a password: no id_token tells ProConnect which session to close.
        user = UserFactory(password="password", confirmed_at=datetime.now())
        self.post(url_for("security.login"), {"email": user.email, "password": "password"})
        self.assert_logged_in_as(user)

        response = self.get(url_for("api.proconnect_reauth"))

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_unavailable"

    def test_login_over_a_session_does_not_inherit_its_grace_period(self, proconnect):
        UserFactory(email="john@example.org")
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "john@example.org")
        self.reauthenticate(proconnect)
        # A sensitive operation starts the grace period of John's session.
        assert self.is_fresh()

        self.sign_in(proconnect, "jane@example.org")

        assert not self.is_fresh()

    def test_abandoned_reauthentication_does_not_apply_to_the_next_login(self, proconnect):
        UserFactory(email="jane@example.org")
        john = UserFactory(email="john@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.start_reauthentication(proconnect)

        response = self.sign_in(proconnect, "john@example.org")

        assert "flash=connected" in response.location
        self.assert_logged_in_as(john)

    def test_abandoned_reauthentication_does_not_turn_the_logout_into_a_login(self, proconnect):
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        # Left at ProConnect, before it signs the agent out.
        self.get(url_for("api.proconnect_reauth"))

        # How cdata logs out.
        response = self.post(url_for("security.logout"), headers={"Accept": "application/json"})
        signed_out = proconnect.end_session(response.json["proconnect_logout_url"])
        response = self.get(url_for("api.proconnect_logout", **signed_out))

        assert response.location == url_for("security.logout")
