from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from authlib.integrations.base_client import OAuthError
from flask import g, url_for

from udata.commands.fixtures import UserFactory
from udata.tests.api import PytestOnlyAPITestCase

CDATA_BASE_URL = "https://data.gouv.fr"


def proconnect_userinfo(email, **kwargs):
    return {"email": email, "given_name": "Jane", "usual_name": "Doe", **kwargs}


# Freshness only travels in the session cookie, so these tests need it to survive from one
# request to the next: over plain http (hence not `Secure`) and on the test SERVER_NAME
# (hence no domain, which a developer's local `udata.cfg` would otherwise pin elsewhere).
@pytest.mark.options(
    CDATA_BASE_URL=CDATA_BASE_URL,
    SECURITY_TWO_FACTOR=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_DOMAIN=None,
)
class ProconnectVerifyAPITest(PytestOnlyAPITestCase):
    """Reauthentication ("sudo mode") through ProConnect."""

    PASSWORD = "Password123"

    def login_through_client(self, **kwargs):
        """Sign in over HTTP, so that freshness lives in a real session cookie."""
        user = UserFactory(password=self.PASSWORD, confirmed_at=datetime.now(UTC), **kwargs)
        response = self.post(
            url_for("security.login"), {"email": user.email, "password": self.PASSWORD}
        )
        self.assertStatus(response, 200)
        return user

    def stale_the_session(self):
        """Age the session past SECURITY_FRESHNESS, as a day-old session would be."""
        self.start_a_new_browser_request()
        with self.client.session_transaction() as session:
            session["fs_paa"] = 0
            session.pop("fs_gexp", None)

    def start_a_new_browser_request(self):
        """Drop everything the next request should re-read from the cookie.

        pytest-flask pushes one application context for the whole test and the test
        client reuses it, so `g` — where flask-login caches the loaded user and
        flask-security the freshness timestamp — leaks from one request to the next.
        A browser carries nothing but its cookies.
        """
        for cached in ("_login_user", "fs_paa", "fs_authn_via"):
            g.pop(cached, None)

    def get_two_factor_setup(self):
        """The freshness-gated call cdata makes, with the Accept header it sends."""
        self.start_a_new_browser_request()
        return self.get(
            url_for("security.two_factor_setup"), headers={"Accept": "application/json"}
        )

    def proconnect_returns(self, **kwargs):
        """Stand in for the ProConnect round-trip the callback would complete."""
        self.start_a_new_browser_request()
        with patch("udata.auth.proconnect.fetch_proconnect_userinfo", **kwargs):
            return self.get(url_for("api.proconnect_verify_auth"))

    def test_verify_start_redirects_anonymous_to_the_homepage(self):
        response = self.get(url_for("api.proconnect_verify"))

        self.assertStatus(response, 302)
        assert response.location.startswith(CDATA_BASE_URL)

    def test_verify_start_sends_the_user_to_proconnect(self):
        self.login_through_client()

        with patch("udata.auth.proconnect.oauth") as oauth:
            self.get(url_for("api.proconnect_verify"))

        redirect_uri = oauth.proconnect.authorize_redirect.call_args.args[0]
        assert redirect_uri.endswith(url_for("api.proconnect_verify_auth"))

    def test_verify_start_never_reuses_the_login_callback(self):
        """The login callback logs the returned identity in; the verify one must not."""
        self.login_through_client()

        with patch("udata.auth.proconnect.oauth") as oauth:
            self.get(url_for("api.proconnect_verify"))

        redirect_uri = oauth.proconnect.authorize_redirect.call_args.args[0]
        assert not redirect_uri.endswith(url_for("api.proconnect_auth"))

    def test_matching_identity_makes_the_session_fresh_again(self):
        user = self.login_through_client(email="jane@example.org")
        self.stale_the_session()

        # Before: flask-security refuses to touch the 2FA setup on a stale session.
        response = self.get_two_factor_setup()
        self.assertStatus(response, 401)
        assert response.json["response"]["reauth_required"] is True

        response = self.proconnect_returns(return_value=proconnect_userinfo(user.email))

        self.assertStatus(response, 302)
        assert response.location == f"{CDATA_BASE_URL}/verify?flash=reauth_success"

        # After: the very same call goes through.
        response = self.get_two_factor_setup()
        self.assertStatus(response, 200)

    def test_another_identity_is_refused_and_never_switches_account(self):
        user = self.login_through_client(email="jane@example.org")
        other = UserFactory(email="john@example.org", confirmed_at=datetime.now(UTC))
        self.stale_the_session()

        response = self.proconnect_returns(return_value=proconnect_userinfo(other.email))

        self.assertStatus(response, 302)
        assert response.location == f"{CDATA_BASE_URL}/verify?flash=reauth_identity_mismatch"

        # Still stale, and still the same user.
        response = self.get_two_factor_setup()
        self.assertStatus(response, 401)

        response = self.get(url_for("api.me"))
        assert response.json["email"] == user.email

    def test_cancelling_on_proconnect_lands_back_on_the_verify_page(self):
        self.login_through_client()

        response = self.proconnect_returns(side_effect=OAuthError(error="access_denied"))

        self.assertStatus(response, 302)
        assert response.location == f"{CDATA_BASE_URL}/verify?flash=reauth_error"

    def test_verify_callback_refuses_anonymous_callers(self):
        with patch("udata.auth.proconnect.fetch_proconnect_userinfo") as fetch:
            response = self.get(url_for("api.proconnect_verify_auth"))

        self.assertStatus(response, 302)
        fetch.assert_not_called()


class VerifyPasswordAPITest(PytestOnlyAPITestCase):
    def test_passwordless_account_gets_an_error_not_a_crash(self):
        """A ProConnect-only account has no hash to compare against: passlib raises on it."""
        user = UserFactory(confirmed_at=datetime.now(UTC))
        user.password = None
        user.save()
        self.login(user)

        response = self.post(url_for("security.verify"), {"password": "whatever"})

        self.assertStatus(response, 400)
        assert response.json["response"]["field_errors"]["password"]

    def test_wrong_password_is_still_refused(self):
        user = UserFactory(password="password123", confirmed_at=datetime.now(UTC))
        self.login(user)

        response = self.post(url_for("security.verify"), {"password": "wrong"})

        self.assertStatus(response, 400)


class HasPasswordFieldTest(PytestOnlyAPITestCase):
    def test_me_tells_whether_the_account_has_a_password(self):
        user = UserFactory(password="password123", confirmed_at=datetime.now(UTC))
        self.login(user)

        assert self.get(url_for("api.me")).json["has_password"] is True

    def test_me_reports_a_proconnect_account_as_passwordless(self):
        user = UserFactory(confirmed_at=datetime.now(UTC))
        user.password = None
        user.save()
        self.login(user)

        assert self.get(url_for("api.me")).json["has_password"] is False

    def test_other_users_never_expose_it(self):
        other = UserFactory(password="password123", confirmed_at=datetime.now(UTC))
        self.login(UserFactory(confirmed_at=datetime.now(UTC)))

        response = self.get(url_for("api.user", user=other))

        assert response.json["has_password"] is None
