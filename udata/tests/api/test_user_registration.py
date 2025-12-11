import pytest
from flask import url_for

from udata.core.user.factories import UserFactory
from udata.models import User
from udata.tests.helpers import capture_mails

from . import APITestCase


@pytest.mark.options(CAPTCHETAT_BASE_URL=None)
class UserRegistrationAPITest(APITestCase):
    def test_registration_success(self):
        """It should create a user and send confirmation email"""
        data = {
            "email": "newuser@example.com",
            "password": "StrongPass123",
            "password_confirmation": "StrongPass123",
            "first_name": "Test",
            "last_name": "User",
            "accept_conditions": True,
        }
        with capture_mails() as mails:
            response = self.post(url_for("api.users"), data)

        self.assert201(response)
        assert "message" in response.json

        user = User.objects.get(email=data["email"])
        assert user is not None
        assert user.first_name == "Test"
        assert user.last_name == "User"
        # In test mode (SEND_MAIL=False), user is auto-confirmed
        assert user.confirmed_at is not None
        assert user.active is True

        assert len(mails) == 1
        assert "confirm" in mails[0].subject.lower()  # "Confirmez" en français

    def test_registration_duplicate_email_sends_existing_account_mail(self):
        """It should return 201 and send existing account email for duplicate email"""
        UserFactory(email="existing@example.com")
        data = {
            "email": "existing@example.com",
            "password": "StrongPass123",
            "password_confirmation": "StrongPass123",
            "first_name": "Test",
            "last_name": "User",
            "accept_conditions": True,
        }
        with capture_mails() as mails:
            response = self.post(url_for("api.users"), data)

        self.assert201(response)

        assert User.objects.count() == 1

        assert len(mails) == 1
        assert "déjà" in mails[0].subject.lower()

    def test_registration_weak_password(self):
        """It should reject weak passwords"""
        data = {
            "email": "newuser@example.com",
            "password": "weak",
            "password_confirmation": "weak",
            "first_name": "Test",
            "last_name": "User",
            "accept_conditions": True,
        }
        response = self.post(url_for("api.users"), data)
        self.assert400(response)

    def test_registration_password_mismatch(self):
        """It should reject mismatched password confirmation"""
        data = {
            "email": "newuser@example.com",
            "password": "StrongPass123",
            "password_confirmation": "DifferentPass123",
            "first_name": "Test",
            "last_name": "User",
            "accept_conditions": True,
        }
        response = self.post(url_for("api.users"), data)
        self.assert400(response)

    def test_registration_url_in_name(self):
        """It should reject URLs in first/last name"""
        data = {
            "email": "newuser@example.com",
            "password": "StrongPass123",
            "password_confirmation": "StrongPass123",
            "first_name": "Test http://spam.com",
            "last_name": "User",
            "accept_conditions": True,
        }
        response = self.post(url_for("api.users"), data)
        self.assert400(response)

    def test_registration_read_only_mode(self):
        """It should reject registration in read-only mode"""
        self.app.config["READ_ONLY_MODE"] = True
        data = {
            "email": "newuser@example.com",
            "password": "StrongPass123",
            "password_confirmation": "StrongPass123",
            "first_name": "Test",
            "last_name": "User",
            "accept_conditions": True,
        }
        response = self.post(url_for("api.users"), data)
        self.assertStatus(response, 423)

    def test_registration_without_accept_conditions(self):
        """It should reject registration without accepting conditions"""
        data = {
            "email": "newuser@example.com",
            "password": "StrongPass123",
            "password_confirmation": "StrongPass123",
            "first_name": "Test",
            "last_name": "User",
            "accept_conditions": False,
        }
        response = self.post(url_for("api.users"), data)
        self.assert400(response)
