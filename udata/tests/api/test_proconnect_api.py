from datetime import datetime

import pytest
from flask import current_app, url_for
from flask_security.recoverable import generate_reset_password_token

from udata.core.api_token.models import ApiToken
from udata.core.user.factories import AdminFactory, UserFactory
from udata.core.user.models import User
from udata.i18n import gettext as _
from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import capture_mails

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

    def sign_in(
        self,
        proconnect,
        email,
        second_factor=True,
        sub=None,
        amr=None,
        require_second_factor: bool | None = None,
    ):
        """`require_second_factor` is what the agent's browser makes of the redirection."""
        proconnect.agent_has_session(email, second_factor=second_factor, sub=sub, amr=amr)
        authorize_url = self.get(url_for("api.proconnect_login")).location
        if require_second_factor is not None:
            authorize_url = proconnect.tamper(
                authorize_url, require_second_factor=require_second_factor
            )
        callback = proconnect.authorize(authorize_url)
        return self.get(url_for("api.proconnect_auth", **callback))

    def set_up_two_factor(self, setup):
        return self.post(
            url_for("security.two_factor_setup"),
            {"setup": setup},
            headers={"Accept": "application/json"},
        )

    def assert_two_factor_setup_refused(self, response):
        self.assert400(response)
        assert response.json["response"]["field_errors"]["setup"] == [
            _(
                "Your account is protected by the two-factor authentication of ProConnect: "
                "sign in with ProConnect to set up another one."
            )
        ]

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

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_first_second_factor_of_an_account_without_udata_2fa_is_trusted(self, proconnect):
        user = UserFactory(email="jane@example.org")

        response = self.sign_in(proconnect, "jane@example.org")

        assert "flash=connected" in response.location
        identity = self.identity_of(user)
        assert identity.sub == "sub-of-jane@example.org"
        assert identity.second_factor
        assert identity.verified_at

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=False)
    def test_first_second_factor_is_trusted_even_when_proconnect_does_not_require_it(
        self, proconnect
    ):
        user = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        assert self.identity_of(user).verified_at
        self.get(url_for("security.logout"))

        # ProConnect doesn't ask an agent with an authenticator app for it unless required.
        response = self.sign_in(proconnect, "jane@example.org", second_factor=False)

        self.assert401(self.get(url_for("api.me")))
        callback = proconnect.authorize(response.location)
        self.get(url_for("api.proconnect_auth", **callback))
        assert proconnect.second_factors == 1
        self.assert_logged_in_as(user)

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_login_sent_back_for_the_second_factor_is_refused_if_it_comes_back_without(
        self, proconnect
    ):
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.get(url_for("security.logout"))
        # Her identity provider now only sends her a code by email, whatever is required.
        response = self.sign_in(proconnect, "jane@example.org", amr=["pwd", "mail", "mfa"])
        callback = proconnect.authorize(response.location)

        response = self.get(url_for("api.proconnect_auth", **callback))

        assert response.location.endswith("flash=proconnect_second_factor_required")
        self.assert401(self.get(url_for("api.me")))

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_login_sent_back_for_the_second_factor_and_abandoned_does_not_refuse_the_next(
        self, proconnect
    ):
        user = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.get(url_for("security.logout"))
        # Sent back to ProConnect for her key, she closes the tab.
        self.sign_in(proconnect, "jane@example.org", amr=["pwd", "mail", "mfa"])

        # She signs in again, and this time presents her key once sent back for it.
        response = self.sign_in(
            proconnect, "jane@example.org", second_factor=False, require_second_factor=False
        )
        callback = proconnect.authorize(response.location)
        self.get(url_for("api.proconnect_auth", **callback))

        self.assert_logged_in_as(user)

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_login_without_the_second_factor_proconnect_holds_is_sent_back_for_it(self, proconnect):
        user = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.get(url_for("security.logout"))
        # The request we send goes through the browser, which may drop the requirement.
        response = self.sign_in(
            proconnect, "jane@example.org", second_factor=False, require_second_factor=False
        )

        self.assert401(self.get(url_for("api.me")))
        # Back at ProConnect, the second factor is asked for: Jane presents it.
        callback = proconnect.authorize(response.location)
        self.get(url_for("api.proconnect_auth", **callback))
        assert proconnect.second_factors == 1
        self.assert_logged_in_as(user)

    def test_login_without_second_factor_does_not_trust_the_identity(self, proconnect):
        user = UserFactory(email="jane@example.org")

        self.sign_in(proconnect, "jane@example.org", second_factor=False)

        self.assert_logged_in_as(user)
        identity = self.identity_of(user)
        assert identity.sub == "sub-of-jane@example.org"
        assert not identity.second_factor
        assert identity.verified_at is None

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_another_identity_is_refused_when_proconnect_holds_the_second_factor(self, proconnect):
        user = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.get(url_for("security.logout"))

        response = self.sign_in(proconnect, "jane@example.org", sub="attacker")

        assert "flash=proconnect_identity_mismatch" in response.location
        self.assert401(self.get(url_for("api.me")))
        assert self.identity_of(user).sub == "sub-of-jane@example.org"

    @pytest.mark.options(
        SECURITY_TWO_FACTOR_REQUIRED_FOR_ADMIN=True, PROCONNECT_REQUIRE_SECOND_FACTOR=True
    )
    def test_sysadmin_without_udata_2fa_signs_in_with_the_proconnect_second_factor(
        self, proconnect
    ):
        admin = AdminFactory(email="admin@example.org")

        response = self.sign_in(proconnect, "admin@example.org")

        assert "flash=connected" in response.location
        self.assert_logged_in_as(admin)
        assert not User.objects.get(id=admin.id).tf_primary_method

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_another_identity_at_the_same_address_cannot_reauthenticate(self, proconnect):
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        response = self.start_reauthentication(proconnect)
        # On Jane's unattended session, someone with their own identity at her address.
        proconnect.agent_sub = "attacker"

        callback = proconnect.authorize(response.location)
        response = self.get(url_for("api.proconnect_auth", **callback))

        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_identity_mismatch"
        assert not self.is_fresh()

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_new_identity_passing_the_udata_2fa_becomes_the_trusted_one(self, proconnect):
        # Jane moved to another identity provider: her udata code proves it's her.
        user, secret = self.totp_user(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.enter_totp(secret)
        self.get(url_for("security.logout"))

        self.sign_in(proconnect, "jane@example.org", sub="new-jane")
        self.assert200(self.enter_totp(secret))

        identity = self.identity_of(user)
        assert identity.sub == "new-jane"
        assert identity.verified_at

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_udata_2fa_cannot_be_set_up_from_a_login_without_the_proconnect_second_factor(
        self, proconnect
    ):
        # Jane's identity is trusted, but this login didn't present its second factor: the
        # udata code stood for it. Then she drops the udata 2FA, ProConnect's being the only.
        _user, secret = self.totp_user(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.enter_totp(secret)
        self.get(url_for("security.logout"))
        self.sign_in(
            proconnect, "jane@example.org", second_factor=False, require_second_factor=False
        )
        self.enter_totp(secret)
        self.assert200(self.set_up_two_factor("disable"))

        response = self.set_up_two_factor("authenticator")

        self.assert_two_factor_setup_refused(response)

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
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

        response = self.set_up_two_factor("authenticator")

        self.assert_two_factor_setup_refused(response)

    @pytest.mark.options(
        SECURITY_TWO_FACTOR_REQUIRED_FOR_ADMIN=True, PROCONNECT_REQUIRE_SECOND_FACTOR=True
    )
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
        response = self.set_up_two_factor("authenticator")

        self.assert_two_factor_setup_refused(response)

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_udata_2fa_can_be_set_up_from_the_trusted_proconnect_login(self, proconnect):
        UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.reauthenticate(proconnect)

        response = self.set_up_two_factor("authenticator")

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

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_the_account_security_is_shown_to_the_user(self, proconnect):
        UserFactory(email="jane@example.org", password="password")
        self.sign_in(proconnect, "jane@example.org")

        response = self.get(url_for("api.me"))

        assert response.json["has_password"] is True
        assert response.json["has_two_factor"] is False
        assert response.json["proconnect"]["sub"] == "sub-of-jane@example.org"
        assert response.json["proconnect"]["second_factor"] is True
        assert response.json["proconnect"]["verified_at"]
        assert response.json["can_switch_to_proconnect_only"] is True

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
        assert response.json["can_switch_to_proconnect_only"] is None

    def switch_to_proconnect_only(self):
        return self.post(url_for("api.proconnect_only"), headers={"Accept": "application/json"})

    def proconnect_only_user(self, proconnect, email="jane@example.org"):
        """An account whose ProConnect identity holds the only second factor, without password."""
        self.sign_in(proconnect, email)
        self.get(url_for("security.logout"))
        user = User.objects.get(email=email)
        assert user.signs_in_with_proconnect_only
        return user

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_switching_to_proconnect_only_drops_the_password_and_the_udata_2fa(self, proconnect):
        user, secret = self.totp_user(
            email="jane@example.org", password="password", confirmed_at=datetime.now()
        )
        self.sign_in(proconnect, "jane@example.org")
        self.enter_totp(secret)
        self.reauthenticate(proconnect)

        with capture_mails() as mails:
            response = self.switch_to_proconnect_only()

        self.assertStatus(response, 204)
        user.reload()
        assert not user.password
        assert not user.tf_primary_method
        assert not user.tf_totp_secret
        assert [mail.recipients for mail in mails] == [["jane@example.org"]]
        self.assert_logged_in_as(user)
        # The session can set up a udata 2FA again, its login being the account's anew.
        self.assert200(self.set_up_two_factor("authenticator"))
        self.get(url_for("security.logout"))
        self.post(url_for("security.login"), {"email": user.email, "password": "password"})
        self.assert401(self.get(url_for("api.me")))

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=False)
    def test_switching_to_proconnect_only_does_not_need_proconnect_to_require_the_second_factor(
        self, proconnect
    ):
        # A later login without it is sent back to ProConnect with it required.
        user, secret = self.totp_user(
            email="jane@example.org", password="password", confirmed_at=datetime.now()
        )
        self.sign_in(proconnect, "jane@example.org")
        self.enter_totp(secret)
        self.reauthenticate(proconnect)

        self.assertStatus(self.switch_to_proconnect_only(), 204)
        assert not User.objects.get(id=user.id).password

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_account_that_already_signs_in_with_proconnect_only_cannot_switch_again(
        self, proconnect
    ):
        self.proconnect_only_user(proconnect)
        self.sign_in(proconnect, "jane@example.org")
        self.reauthenticate(proconnect)
        assert self.get(url_for("api.me")).json["can_switch_to_proconnect_only"] is False

        with capture_mails() as mails:
            response = self.switch_to_proconnect_only()

        self.assert400(response)
        assert mails == []
        self.assert_logged_in_as(User.objects.get(email="jane@example.org"))

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_account_without_password_switches_to_drop_its_udata_2fa(self, proconnect):
        # A udata 2FA set up from a trusted ProConnect login, on an account created by it.
        user = self.proconnect_only_user(proconnect)
        user.update(tf_primary_method="authenticator", tf_totp_secret="secret")
        self.sign_in(proconnect, "jane@example.org")
        self.reauthenticate(proconnect)
        assert self.get(url_for("api.me")).json["can_switch_to_proconnect_only"] is True

        self.assertStatus(self.switch_to_proconnect_only(), 204)

        assert not User.objects.get(id=user.id).tf_primary_method

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_switching_to_proconnect_only_keeps_the_api_keys(self, proconnect):
        # Scripts depend on them.
        user = UserFactory(email="jane@example.org", password="password")
        _, plaintext = ApiToken.generate(user)
        self.sign_in(proconnect, "jane@example.org")
        self.reauthenticate(proconnect)

        self.assertStatus(self.switch_to_proconnect_only(), 204)

        with current_app.app_context():
            response = current_app.test_client().get(
                url_for("api.me"), headers={"X-API-KEY": plaintext}
            )
        self.assert200(response)

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=False)
    def test_login_with_a_password_left_invites_to_switch_to_proconnect_only(self, proconnect):
        UserFactory(email="jane@example.org", password="password")

        response = self.sign_in(proconnect, "jane@example.org")

        assert "flash=proconnect_only_available" in response.location

    def test_login_without_second_factor_does_not_invite_to_switch(self, proconnect):
        UserFactory(email="jane@example.org", password="password")

        response = self.sign_in(proconnect, "jane@example.org", second_factor=False)

        assert "flash=connected" in response.location

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_switching_to_proconnect_only_signs_out_the_other_sessions(self, proconnect):
        user = UserFactory(
            email="jane@example.org", password="password", confirmed_at=datetime.now()
        )
        elsewhere = current_app.test_client()
        elsewhere.post(
            url_for("security.login"), data={"email": user.email, "password": "password"}
        )
        with current_app.app_context():
            assert elsewhere.get(url_for("api.me")).status_code == 200
        self.sign_in(proconnect, "jane@example.org")
        self.reauthenticate(proconnect)

        self.assertStatus(self.switch_to_proconnect_only(), 204)

        with current_app.app_context():
            assert elsewhere.get(url_for("api.me")).status_code == 401
        self.assert_logged_in_as(user)

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_switching_to_proconnect_only_requires_a_fresh_session(self, proconnect):
        UserFactory(email="jane@example.org", password="password")
        self.sign_in(proconnect, "jane@example.org")

        response = self.switch_to_proconnect_only()

        self.assert401(response)
        assert response.json["response"]["reauth_required"]

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_switching_to_proconnect_only_requires_the_trusted_proconnect_identity(
        self, proconnect
    ):
        # Signed in with the password: whoever has it doesn't prove the ProConnect key.
        user = UserFactory(
            email="jane@example.org", password="password", confirmed_at=datetime.now()
        )
        self.sign_in(proconnect, "jane@example.org")
        self.get(url_for("security.logout"))
        self.post(url_for("security.login"), {"email": user.email, "password": "password"})
        assert self.is_fresh()

        self.assert403(self.switch_to_proconnect_only())
        assert User.objects.get(id=user.id).password

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_switching_to_proconnect_only_requires_its_second_factor(self, proconnect):
        # Jane's identity is trusted, but this login didn't present its second factor: her
        # udata code stood for it.
        user, secret = self.totp_user(
            email="jane@example.org", password="password", confirmed_at=datetime.now()
        )
        self.sign_in(proconnect, "jane@example.org")
        self.enter_totp(secret)
        self.get(url_for("security.logout"))
        self.sign_in(
            proconnect, "jane@example.org", second_factor=False, require_second_factor=False
        )
        self.enter_totp(secret)
        self.reauthenticate(proconnect)

        self.assert403(self.switch_to_proconnect_only())
        assert User.objects.get(id=user.id).password

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_reset_cannot_give_a_password_to_an_account_that_signs_in_with_proconnect_only(
        self, proconnect
    ):
        user = self.proconnect_only_user(proconnect)

        response = self.post(
            url_for("security.reset_password", token=generate_reset_password_token(user)),
            {"password": "Attacker-Pass-1337", "password_confirm": "Attacker-Pass-1337"},
            headers={"Accept": "application/json"},
        )

        self.assert400(response)
        assert not User.objects.get(id=user.id).password

    def test_reset_gives_a_password_to_an_account_without_any_second_factor(self, proconnect):
        # Created by ProConnect, without a second factor: a password opens nothing more than
        # the mailbox already does.
        self.sign_in(proconnect, "jane@example.org", second_factor=False)
        self.get(url_for("security.logout"))
        user = User.objects.get(email="jane@example.org")

        response = self.post(
            url_for("security.reset_password", token=generate_reset_password_token(user)),
            {"password": "Jane-Pass-1337", "password_confirm": "Jane-Pass-1337"},
            headers={"Accept": "application/json"},
        )

        self.assert200(response)
        assert User.objects.get(id=user.id).password

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True, CAPTCHETAT_BASE_URL=None)
    def test_reset_mail_of_an_account_that_signs_in_with_proconnect_only_sends_to_it(
        self, proconnect
    ):
        user = self.proconnect_only_user(proconnect)

        with capture_mails() as mails:
            response = self.post(
                url_for("security.forgot_password"),
                {"email": user.email},
                headers={"Accept": "application/json"},
            )

        self.assert200(response)
        assert [mail.recipients for mail in mails] == [["jane@example.org"]]
        assert _("Your account has no password: it signs in with ProConnect only.") in mails[0].body
        assert f"{CDATA}/login" in mails[0].body
        assert "/reset/" not in mails[0].body

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_change_password_cannot_give_a_password_to_an_account_that_signs_in_with_proconnect_only(
        self, proconnect
    ):
        user = self.proconnect_only_user(proconnect)
        self.sign_in(proconnect, "jane@example.org")
        self.reauthenticate(proconnect)

        response = self.post(
            url_for("security.change_password"),
            {"new_password": "Attacker-Pass-1337", "new_password_confirm": "Attacker-Pass-1337"},
            headers={"Accept": "application/json"},
        )

        self.assert400(response)
        assert not User.objects.get(id=user.id).password

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_trusted_identity_finds_its_account_after_its_address_changed(self, proconnect):
        user = UserFactory(email="jane@old-domain.fr")
        self.sign_in(proconnect, "jane@old-domain.fr", sub="jane")
        self.get(url_for("security.logout"))

        self.sign_in(proconnect, "jane@new-domain.fr", sub="jane")

        self.assert_logged_in_as(user)
        assert not User.objects(email="jane@new-domain.fr")
        response = self.reauthenticate(proconnect)
        assert response.location == f"{CDATA}/verify?flash=proconnect_reauth_success"

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_trusted_identity_finds_its_account_before_the_one_at_its_address(self, proconnect):
        user = UserFactory(email="jane@old-domain.fr")
        self.sign_in(proconnect, "jane@old-domain.fr", sub="jane")
        self.get(url_for("security.logout"))
        UserFactory(email="jane@new-domain.fr")

        self.sign_in(proconnect, "jane@new-domain.fr", sub="jane")

        self.assert_logged_in_as(user)

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_deleted_account_is_not_found_by_its_trusted_identity(self, proconnect):
        user = UserFactory(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.get(url_for("security.logout"))
        User.objects.get(id=user.id).mark_as_deleted(notify=False)

        response = self.sign_in(proconnect, "jane@example.org")

        assert "flash=connected" in response.location
        assert User.objects(email="jane@example.org", deleted=None).count() == 1

    def test_identity_not_trusted_does_not_follow_an_address_change(self, proconnect):
        user = UserFactory(email="jane@old-domain.fr")
        self.sign_in(proconnect, "jane@old-domain.fr", sub="jane", second_factor=False)
        self.get(url_for("security.logout"))

        self.sign_in(proconnect, "jane@new-domain.fr", sub="jane", second_factor=False)

        assert User.objects.get(email="jane@new-domain.fr").id != user.id

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_one_time_code_by_email_is_no_second_factor(self, proconnect):
        # ProConnect adds one for an identity provider without a second factor: it only proves
        # access to the mailbox again.
        user = UserFactory(email="jane@example.org")

        self.sign_in(proconnect, "jane@example.org", amr=["pwd", "mail", "mfa"])

        identity = self.identity_of(user)
        assert not identity.second_factor
        assert identity.verified_at is None

    @pytest.mark.options(PROCONNECT_REQUIRE_SECOND_FACTOR=True)
    def test_one_time_code_by_email_does_not_skip_the_udata_second_factor(self, proconnect):
        _, secret = self.totp_user(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")
        self.enter_totp(secret)
        self.get(url_for("security.logout"))

        # Her trusted identity, signing in with a code by email instead of her key.
        self.sign_in(proconnect, "jane@example.org", amr=["pwd", "mail", "mfa"])

        self.assert401(self.get(url_for("api.me")))

    def test_login_completed_by_the_two_factor_is_fresh(self, proconnect):
        # A code from the agent's authenticator proves as much as a password on /verify.
        _, secret = self.totp_user(email="jane@example.org")
        self.sign_in(proconnect, "jane@example.org")

        response = self.enter_totp(secret)

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
        proconnect.agent_sub = "sub-of-john@example.org"

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
