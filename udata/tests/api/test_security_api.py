from datetime import datetime

import pytest
from flask import url_for
from flask_login import current_user
from flask_security.recoverable import generate_reset_password_token

from udata.auth.forms import ExtendedLoginForm
from udata.commands.fixtures import UserFactory
from udata.i18n import lazy_gettext as _
from udata.tests.api import PytestOnlyAPITestCase
from udata.tests.helpers import capture_mails


class SecurityAPITest(PytestOnlyAPITestCase):
    @pytest.mark.options(CAPTCHETAT_BASE_URL=None)
    def test_register(self):
        # We cannot test for mail sending since they are sent with Flask
        # directly and not with our system but if the sending is working
        # we test the rendering of the mail.

        response = self.post(
            url_for("security.register"),
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "accept_conditions": True,
                "email": "jane@example.org",
                "password": "Password123",
                "password_confirm": "Password123",
                "submit": True,
            },
        )
        self.assertStatus(response, 200)

    @pytest.mark.options(CAPTCHETAT_BASE_URL=None, SECURITY_RETURN_GENERIC_RESPONSES=True)
    def test_register_existing(self):
        # We cannot test for mail sending since they are sent with Flask
        # directly and not with our system but if the sending is working
        # we test the rendering of the mail.

        UserFactory(email="jane@example.org", confirmed_at=datetime.now())
        response = self.post(
            url_for("security.register"),
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "accept_conditions": True,
                "email": "jane@example.org",
                "password": "Password123",
                "password_confirm": "Password123",
                "submit": True,
            },
        )
        self.assertStatus(response, 200)

    @pytest.mark.options(CAPTCHETAT_BASE_URL=None)
    def test_ask_for_reset(self):
        # We cannot test for mail sending since they are sent with Flask
        # directly and not with our system but if the sending is working
        # we test the rendering of the mail.

        UserFactory(email="jane@example.org", confirmed_at=datetime.now())

        response = self.post(
            url_for("security.forgot_password"), {"email": "jane@example.org", "submit": True}
        )
        self.assertStatus(response, 200)

    @pytest.mark.options(CAPTCHETAT_BASE_URL=None)
    def test_change_notice_mail(self):
        # We cannot test for mail sending since they are sent with Flask
        # directly and not with our system but if the sending is working
        # we test the rendering of the mail.

        user = UserFactory(
            email="jane@example.org", password="password", confirmed_at=datetime.now()
        )
        self.login(user)

        response = self.post(
            url_for("security.change_password"),
            {
                "password": "password",
                "new_password": "New_password123",
                "new_password_confirm": "New_password123",
                "submit": True,
            },
        )
        self.assertStatus(response, 200)

    @pytest.mark.options(CAPTCHETAT_BASE_URL=None)
    def test_change_email_confirmation(self):
        user = UserFactory(email="jane@example.org", confirmed_at=datetime.now())
        self.login(user)

        with capture_mails() as mails:
            response = self.post(
                url_for("security.change_email"),
                {
                    "new_email": "jane2@example.org",
                    "new_email_confirm": "jane2@example.org",
                    "submit": True,
                },
            )
            self.assertStatus(response, 200)

        assert len(mails) == 1
        assert len(mails[0].recipients) == 1
        assert mails[0].recipients[0] == "jane2@example.org"
        assert mails[0].subject == _("Confirm your email address")

    @pytest.mark.options(CAPTCHETAT_BASE_URL=None, SECURITY_RETURN_GENERIC_RESPONSES=True)
    def test_reset_password(self):
        user = UserFactory(email="jane@example.org", confirmed_at=datetime.now())
        token = generate_reset_password_token(user)

        response = self.post(
            url_for("security.reset_password", token=token),
            {
                "password": "Password123",
                "password_confirm": "Password123",
                "submit": True,
            },
        )
        self.assertStatus(response, 200)

    @pytest.mark.options(CAPTCHETAT_BASE_URL=None, SECURITY_RETURN_GENERIC_RESPONSES=True)
    def test_reset_password_user_not_authenticated_after_reset(self):
        """
        After resetting a password, the user should NOT be automatically logged in, no flash message.
        """
        user = UserFactory(email="jane@example.org", confirmed_at=datetime.now())
        token = generate_reset_password_token(user)

        response = self.post(
            url_for("security.reset_password", token=token),
            {
                "password": "Password123",
                "password_confirm": "Password123",
                "submit": True,
            },
        )
        self.assertStatus(response, 200)

        # Verify user is NOT authenticated after password reset
        assert not current_user.is_authenticated

    @pytest.mark.options(CAPTCHETAT_BASE_URL=None)
    def test_login_with_password_rotation_demanded(self):
        """
        When a user has password_rotation_demanded set, login fail with error message + flag.
        """
        UserFactory(
            email="jane@example.org",
            password="password",
            confirmed_at=datetime.now(),
            password_rotation_demanded=datetime.now(),
        )

        response = self.post(
            url_for("security.login"),
            {
                "email": "jane@example.org",
                "password": "password",
                "submit": True,
            },
        )
        self.assertStatus(response, 400)

        # Verify the response contains the password rotation error
        response_data = response.json
        assert "response" in response_data

        # Flask-Security can return errors as a list or dict depending on configuration
        errors = response_data["response"].get("errors", [])
        expected_error = str(ExtendedLoginForm.PASSWORD_ROTATION_ERROR)

        # Check that the password rotation error is in the errors (handle both list and dict format)
        if isinstance(errors, dict):
            password_errors = errors.get("password", [])
            assert any(
                expected_error in str(err) for err in password_errors
            ), f"Expected '{expected_error}' in password errors, got {password_errors}"
        else:
            # errors is a list of error strings
            assert any(
                expected_error in str(err) for err in errors
            ), f"Expected '{expected_error}' in errors, got {errors}"

        # Check that the password_reset_required flag is set
        assert response_data["response"].get("password_reset_required") is True
        assert "password_reset_url" in response_data["response"]

        # Verify user is NOT authenticated
        assert not current_user.is_authenticated

    @pytest.mark.options(CAPTCHETAT_BASE_URL=None)
    def test_login_with_password_rotation_clears_after_reset(self):
        """
        After resetting password, the password_rotation_demanded should be cleared
        and user should be able to log in.
        See: https://github.com/opendatateam/udata/issues/3540
        """
        user = UserFactory(
            email="jane@example.org",
            password="password",
            confirmed_at=datetime.now(),
            password_rotation_demanded=datetime.now(),
        )

        # Generate reset token and reset password
        token = generate_reset_password_token(user)
        response = self.post(
            url_for("security.reset_password", token=token),
            {
                "password": "NewPassword123",
                "password_confirm": "NewPassword123",
                "submit": True,
            },
        )
        self.assertStatus(response, 200)

        # Reload user from database
        user.reload()

        # Verify password_rotation_demanded is cleared
        assert user.password_rotation_demanded is None
        # Verify password_rotation_performed is set
        assert user.password_rotation_performed is not None

        # Now login should succeed
        response = self.post(
            url_for("security.login"),
            {
                "email": "jane@example.org",
                "password": "NewPassword123",
                "submit": True,
            },
        )
        self.assertStatus(response, 200)

        # Verify no password rotation error in response
        response_data = response.json
        assert response_data["response"].get("password_reset_required") is not True
