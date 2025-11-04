from datetime import datetime

import pytest
from flask import url_for

from udata.commands.fixtures import UserFactory
from udata.tests.api import PytestOnlyAPITestCase


class SecurityAPITest(PytestOnlyAPITestCase):
    @pytest.mark.options(CAPTCHETAT_BASE_URL=None)
    def test_ask_for_reset(self, api, client):
        # We cannot test for mail sending since they are sent with Flask
        # directly and not with our system but if the sending is working
        # we test the rendering of the mail.

        UserFactory(email="jane@example.org", confirmed_at=datetime.now())

        response = api.post(
            url_for("security.forgot_password"), {"email": "jane@example.org", "submit": True}
        )
        self.assertStatus(response, 200)

    @pytest.mark.options(CAPTCHETAT_BASE_URL=None)
    def test_change_password(self, api, client):
        # We cannot test for mail sending since they are sent with Flask
        # directly and not with our system but if the sending is working
        # we test the rendering of the mail.

        user = UserFactory(
            email="jane@example.org", password="password", confirmed_at=datetime.now()
        )
        self.login(user)

        response = api.post(
            url_for("security.change_password"),
            {
                "password": "password",
                "new_password": "New_password123",
                "new_password_confirm": "New_password123",
                "submit": True,
            },
        )
        self.assertStatus(response, 200)
