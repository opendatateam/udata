from datetime import datetime

import pytest
from flask import url_for
from flask_security.recoverable import generate_reset_password_token

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
