from datetime import timedelta
from unittest import mock

from flask import current_app, url_for
from flask_security.utils import hash_data

from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.models import Member, MembershipRequest
from udata.tests.api import APITestCase


class AuthTest(APITestCase):
    def confirm_change_email(self, user, new_email):
        security = current_app.extensions["security"]
        data = [str(user.fs_uniquifier), hash_data(user.email), new_email]
        token = security.confirm_serializer.dumps(data)
        return self.get(url_for("security.confirm_change_email", token=token))

    def test_change_mail_links_pending_email_invitations(self):
        """An unlinked invitation is invisible to the user, who could only ask to join."""
        user = self.login()
        organization = OrganizationFactory(
            requests=[MembershipRequest(kind="invitation", email="new@example.com")]
        )

        resp = self.confirm_change_email(user, "New@example.com")
        assert resp.status_code == 302

        organization.reload()
        assert organization.requests[0].user == user
        assert organization.requests[0].email is None

    def test_change_mail_drops_email_invitations_of_organizations_already_joined(self):
        user = self.login()
        organization = OrganizationFactory(
            members=[Member(user=user, role="editor")],
            requests=[MembershipRequest(kind="invitation", email="new@example.com")],
        )

        self.confirm_change_email(user, "new@example.com")

        organization.reload()
        assert organization.requests == []

    def test_change_mail_drops_email_invitations_of_organizations_already_requested(self):
        user = self.login()
        membership_request = MembershipRequest(user=user, comment="Please add me")
        organization = OrganizationFactory(
            requests=[
                membership_request,
                MembershipRequest(kind="invitation", email="new@example.com"),
            ]
        )

        self.confirm_change_email(user, "new@example.com")

        organization.reload()
        assert [r.id for r in organization.requests] == [membership_request.id]

    def test_change_mail(self):
        user = self.login(AdminFactory())

        new_email = "test@test.com"

        security = current_app.extensions["security"]

        data = [str(user.fs_uniquifier), hash_data(user.email), new_email]
        token = security.confirm_serializer.dumps(data)
        confirmation_link = url_for("security.confirm_change_email", token=token)

        resp = self.get(confirmation_link)
        assert resp.status_code == 302

        user.reload()
        assert user.email == new_email

    def test_change_mail_expired(self):
        """An expired link sends a new confirmation mail and redirects with a flash"""
        user = self.login(AdminFactory())
        original_email = user.email
        new_email = "test@test.com"

        security = current_app.extensions["security"]

        data = [str(user.fs_uniquifier), hash_data(user.email), new_email]
        token = security.confirm_serializer.dumps(data)
        confirmation_link = url_for("security.confirm_change_email", token=token)

        # A negative validity makes any freshly signed token already expired
        with mock.patch.dict(
            current_app.config, {"SECURITY_CONFIRM_EMAIL_WITHIN": timedelta(seconds=-1)}
        ):
            resp = self.get(confirmation_link)

        assert resp.status_code == 302
        assert "change_email_expired" in resp.location

        user.reload()
        assert user.email == original_email

    def test_change_mail_already_taken(self):
        """Should not allow changing email to one already taken by another user"""
        user = self.login(AdminFactory())
        original_email = user.email

        # Create another user with the target email
        existing_user = UserFactory(email="taken@example.com")
        new_email = existing_user.email

        security = current_app.extensions["security"]

        data = [str(user.fs_uniquifier), hash_data(user.email), new_email]
        token = security.confirm_serializer.dumps(data)
        confirmation_link = url_for("security.confirm_change_email", token=token)

        resp = self.get(confirmation_link)
        assert resp.status_code == 302
        assert "change_email_already_taken" in resp.location

        # Email should not have changed
        user.reload()
        assert user.email == original_email

    def test_change_mail_after_password_change(self):
        """Changing password rotates fs_uniquifier and invalidates email change token"""
        user = UserFactory(password="Password123")
        self.login(user)
        old_uniquifier = user.fs_uniquifier

        new_email = "new@example.com"

        security = current_app.extensions["security"]

        data = [str(user.fs_uniquifier), hash_data(user.email), new_email]
        token = security.confirm_serializer.dumps(data)
        confirmation_link = url_for("security.confirm_change_email", token=token)

        # Change password via API
        resp = self.post(
            url_for("security.change_password"),
            {
                "password": "Password123",
                "new_password": "NewPassword456",
                "new_password_confirm": "NewPassword456",
                "submit": True,
            },
        )
        assert resp.status_code == 200, f"Password change failed: {resp.data}"

        user.reload()
        assert user.fs_uniquifier != old_uniquifier, "fs_uniquifier should have changed"

        # Now try to use the email change link - should fail
        resp = self.get(confirmation_link)
        assert resp.status_code == 302
        assert "change_email_invalid" in resp.location
