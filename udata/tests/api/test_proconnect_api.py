import json
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import pytest
from flask import current_app, url_for

from udata.core.user.factories import AdminFactory, UserFactory
from udata.core.user.models import User
from udata.tests.api import PytestOnlyAPITestCase

CDATA = "http://cdata.test"


def require_second_factor(authorize_url: str) -> str:
    """What an agent's browser can do to the redirection to ProConnect before following it."""
    parts = urlparse(authorize_url)
    params = {key: values[0] for key, values in parse_qs(parts.query).items()}
    params.pop("acr_values", None)
    params["claims"] = json.dumps(
        {"id_token": {"acr": {"essential": True, "values": ["eidas0-mfa"]}, "amr": None}}
    )
    return urlunparse(parts._replace(query=urlencode(params)))


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

    def sign_in(self, proconnect, email, second_factor=True, sub=None):
        proconnect.agent_has_session(email, second_factor=second_factor, sub=sub)
        response = self.get(url_for("api.proconnect_login"))
        callback = proconnect.authorize(response.location)
        return self.get(url_for("api.proconnect_auth", **callback))

    def enter_totp(self, secret):
        totp = current_app.extensions["security"].totp_factory
        return self.post(
            url_for("security.two_factor_token_validation"),
            {"code": totp.generate_totp_password(secret)},
        )

    def totp_user(self, **kwargs):
        secret = current_app.extensions["security"].totp_factory.generate_totp_secret()
        user = UserFactory(tf_primary_method="authenticator", tf_totp_secret=secret, **kwargs)
        return user, secret

    def identity_of(self, user):
        return User.objects.get(id=user.id).proconnect

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

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_login_requires_a_second_factor_at_proconnect(self, proconnect):
        user = UserFactory(email="jane@example.org")
        proconnect.agent_has_session("jane@example.org", second_factor=False)

        response = self.get(url_for("api.proconnect_login"))
        callback = proconnect.authorize(response.location)
        self.get(url_for("api.proconnect_auth", **callback))

        assert proconnect.second_factors == 1
        self.assert_logged_in_as(user)

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=False)
    def test_login_does_not_require_a_second_factor_unless_configured(self, proconnect):
        user = UserFactory(email="jane@example.org")
        proconnect.agent_has_session("jane@example.org", second_factor=False)

        response = self.get(url_for("api.proconnect_login"))
        callback = proconnect.authorize(response.location)
        self.get(url_for("api.proconnect_auth", **callback))

        assert proconnect.second_factors == 0
        self.assert_logged_in_as(user)

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_second_factor_presented_to_proconnect_stands_for_the_udata_one_once_seen_with_it(
        self, proconnect
    ):
        user, secret = self.totp_user(email="jane@example.org")
        # The first time, nothing tells that this identity is Jane's: the udata 2FA does.
        self.sign_in(proconnect, "jane@example.org")
        self.assert401(self.get(url_for("api.me")))
        self.assert200(self.enter_totp(secret))
        assert self.identity_of(user).verified_at
        self.get(url_for("security.logout"))

        response = self.sign_in(proconnect, "jane@example.org")

        assert "flash=connected" in response.location
        self.assert_logged_in_as(user)
        # The second factor may come from a ProConnect session opened earlier.
        assert not self.is_fresh()

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_another_identity_with_a_second_factor_does_not_skip_the_udata_one(self, proconnect):
        user, secret = self.totp_user(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.enter_totp(secret)
        self.get(url_for("security.logout"))

        # Someone who reads Jane's mailbox created a ProConnect identity with her address.
        self.sign_in(proconnect, "jane@example.org", sub="attacker")

        self.assert401(self.get(url_for("api.me")))
        assert self.identity_of(user).sub == "sub-of-jane@example.org"

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=False)
    def test_requiring_a_second_factor_from_the_browser_does_not_skip_the_udata_one(
        self, proconnect
    ):
        # The redirection to ProConnect isn't signed: an agent may require the second factor
        # we don't, and present their own.
        self.totp_user(email="jane@example.org")
        proconnect.agent_has_session("jane@example.org", sub="attacker")
        response = self.get(url_for("api.proconnect_login"))

        callback = proconnect.authorize(require_second_factor(response.location))
        self.get(url_for("api.proconnect_auth", **callback))

        self.assert401(self.get(url_for("api.me")))

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=False)
    def test_identity_seen_without_a_second_factor_is_not_trusted_once_it_has_one(self, proconnect):
        user, secret = self.totp_user(email="jane@example.org")
        # Jane's ProConnect identity has no second factor yet, and none is required.
        self.sign_in(proconnect, "jane@example.org", second_factor=False)
        self.enter_totp(secret)
        assert self.identity_of(user).verified_at is None
        self.get(url_for("security.logout"))

        # Someone reset her ProConnect password from her mailbox and set up their own key.
        self.sign_in(proconnect, "jane@example.org")

        self.assert401(self.get(url_for("api.me")))

    def test_first_second_factor_of_an_account_without_udata_2fa_is_trusted(self, proconnect):
        user = UserFactory(email="jane@example.org")

        response = self.sign_in(proconnect, "jane@example.org")

        assert "flash=connected" in response.location
        identity = self.identity_of(user)
        assert identity.sub == "sub-of-jane@example.org"
        assert identity.second_factor
        assert identity.verified_at

    def test_login_without_second_factor_does_not_trust_the_identity(self, proconnect):
        user = UserFactory(email="jane@example.org")

        self.sign_in(proconnect, "jane@example.org", second_factor=False)

        self.assert_logged_in_as(user)
        identity = self.identity_of(user)
        assert identity.sub == "sub-of-jane@example.org"
        assert not identity.second_factor
        assert identity.verified_at is None

    def test_another_identity_is_refused_when_proconnect_holds_the_second_factor(self, proconnect):
        user = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.get(url_for("security.logout"))

        response = self.sign_in(proconnect, "jane@example.org", sub="attacker")

        assert "flash=proconnect_identity_mismatch" in response.location
        self.assert401(self.get(url_for("api.me")))
        assert self.identity_of(user).sub == "sub-of-jane@example.org"

    @pytest.mark.options(SECURITY_TWO_FACTOR_REQUIRED_FOR_ADMIN=True)
    def test_sysadmin_without_udata_2fa_signs_in_with_the_proconnect_second_factor(
        self, proconnect
    ):
        admin = AdminFactory(email="admin@example.org")

        response = self.sign_in(proconnect, "admin@example.org")

        assert "flash=connected" in response.location
        self.assert_logged_in_as(admin)
        assert not User.objects.get(id=admin.id).tf_primary_method

    @pytest.mark.options(SECURITY_TWO_FACTOR_REQUIRED_FOR_ADMIN=True)
    def test_sysadmin_trusting_proconnect_is_refused_without_its_second_factor(self, proconnect):
        AdminFactory(email="admin@example.org")
        self.sign_in(proconnect, "admin@example.org")
        self.get(url_for("security.logout"))

        response = self.sign_in(proconnect, "admin@example.org", second_factor=False)

        assert "flash=proconnect_second_factor_required" in response.location
        self.assert401(self.get(url_for("api.me")))

    def test_udata_2fa_cannot_be_set_up_by_password_once_proconnect_holds_the_second_factor(
        self, proconnect
    ):
        # Jane trusts her ProConnect key; someone who has her password signs in with it.
        user = UserFactory(
            email="jane@example.org", password="password", confirmed_at=datetime.now()
        )
        self.sign_in(proconnect, "jane@example.org")
        self.get(url_for("security.logout"))
        self.post(url_for("security.login"), {"email": user.email, "password": "password"})
        self.assert_logged_in_as(user)
        assert self.is_fresh()

        response = self.post(
            url_for("security.two_factor_setup"),
            {"setup": "authenticator"},
            headers={"Accept": "application/json"},
        )

        self.assert400(response)
        assert not User.objects.get(id=user.id).tf_totp_secret

    @pytest.mark.options(SECURITY_TWO_FACTOR_REQUIRED_FOR_ADMIN=True)
    def test_sysadmin_trusting_proconnect_cannot_set_up_the_udata_2fa_from_a_password_login(
        self, proconnect
    ):
        # The password may come from a reset, which only takes reading the mailbox.
        admin = AdminFactory(
            email="admin@example.org", password="password", confirmed_at=datetime.now()
        )
        self.sign_in(proconnect, "admin@example.org")
        self.get(url_for("security.logout"))

        response = self.post(
            url_for("security.login"),
            {"email": admin.email, "password": "password"},
            headers={"Accept": "application/json"},
        )
        assert response.json["response"]["tf_state"] == "setup_from_login"
        response = self.post(
            url_for("security.two_factor_setup"),
            {"setup": "authenticator"},
            headers={"Accept": "application/json"},
        )

        self.assert400(response)
        assert not User.objects.get(id=admin.id).tf_totp_secret

    def test_udata_2fa_can_be_set_up_from_the_trusted_proconnect_login(self, proconnect):
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.reauthenticate(proconnect)

        response = self.post(
            url_for("security.two_factor_setup"),
            {"setup": "authenticator"},
            headers={"Accept": "application/json"},
        )

        self.assert200(response)

    def test_proconnect_login_left_waiting_for_the_2fa_is_not_recorded_by_a_password_login(
        self, proconnect
    ):
        user, secret = self.totp_user(
            email="jane@example.org", password="password", confirmed_at=datetime.now()
        )
        # On a shared browser: someone signs in to ProConnect as Jane, and stops at the 2FA.
        self.sign_in(proconnect, "jane@example.org", sub="attacker")

        # Later, Jane signs in with her password and her code.
        self.post(url_for("security.login"), {"email": user.email, "password": "password"})
        self.enter_totp(secret)

        self.assert_logged_in_as(user)
        assert self.identity_of(user) is None

    def test_the_account_security_is_shown_to_the_user(self, proconnect):
        UserFactory(email="jane@example.org", password="password")
        self.sign_in(proconnect, "jane@example.org")

        response = self.get(url_for("api.me"))

        assert response.json["has_password"] is True
        assert response.json["has_two_factor"] is False
        assert response.json["proconnect"]["sub"] == "sub-of-jane@example.org"
        assert response.json["proconnect"]["second_factor"] is True
        assert response.json["proconnect"]["verified_at"]

    def test_the_account_security_is_hidden_from_other_users(self, proconnect):
        jane = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.get(url_for("security.logout"))
        self.sign_in(proconnect, "john@example.org")

        response = self.get(url_for("api.user", user=jane))

        self.assert200(response)
        assert response.json["has_password"] is None
        assert response.json["has_two_factor"] is None
        assert response.json["proconnect"] is None

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=False)
    def test_udata_second_factor_is_asked_when_proconnect_does_not_require_one(self, proconnect):
        totp = current_app.extensions["security"].totp_factory
        UserFactory(
            email="jane@example.org",
            tf_primary_method="authenticator",
            tf_totp_secret=totp.generate_totp_secret(),
        )

        self.sign_in(proconnect, "jane@example.org")

        self.assert401(self.get(url_for("api.me")))

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

        # A second factor at ProConnect would stand for the udata one.
        response = self.sign_in(proconnect, "jane@example.org", second_factor=False)

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
