from datetime import timedelta
from unittest import mock

from flask import current_app, url_for
from flask_security.utils import hash_data

from udata.core.organization.factories import (
    MembershipRequestNotificationFactory,
    OrganizationFactory,
)
from udata.core.user.factories import AdminFactory, UserFactory
from udata.models import Member, MembershipRequest
from udata.tests.api import APITestCase
from udata.tests.helpers import capture_mails


class AuthTest(APITestCase):
    def change_email_link(self, user, new_email):
        security = current_app.extensions["security"]
        data = [str(user.fs_uniquifier), hash_data(user.email), new_email]
        token = security.confirm_serializer.dumps(data)
        return url_for("security.confirm_change_email", token=token)

    def open_expired(self, link):
        with capture_mails() as mails:
            # A negative validity makes any freshly signed token already expired
            with mock.patch.dict(
                current_app.config, {"SECURITY_CONFIRM_EMAIL_WITHIN": timedelta(seconds=-1)}
            ):
                response = self.get(link)
        return response, mails

    def test_change_mail_notifies_the_previous_address(self):
        # Whoever got hold of the account would otherwise move it away unnoticed: the new
        # address confirms the change, so only the previous one can tell its holder.
        user = self.login(UserFactory(email="old@example.com", first_name="Jane"))

        with capture_mails() as mails:
            self.get(self.change_email_link(user, "new@example.com"))

        assert [mail.recipients for mail in mails] == [["old@example.com"]]
        assert "new@example.com" in mails[0].body
        assert "Jane" in mails[0].body
        assert user.reload().email == "new@example.com"

    def test_change_mail_links_pending_email_invitations(self):
        """An unlinked invitation is invisible to the user, who could only ask to join."""
        user = self.login()
        organization = OrganizationFactory(
            requests=[MembershipRequest(kind="invitation", email="new@example.com")]
        )

        self.get(self.change_email_link(user, "New@example.com"))

        organization.reload()
        assert organization.requests[0].user == user
        assert organization.requests[0].email is None

    def test_change_mail_drops_email_invitations_of_organizations_already_joined(self):
        user = self.login()
        organization = OrganizationFactory(
            members=[Member(user=user, role="editor")],
            requests=[MembershipRequest(kind="invitation", email="new@example.com")],
        )

        self.get(self.change_email_link(user, "new@example.com"))

        organization.reload()
        assert organization.requests == []

    def test_change_mail_drops_email_invitations_of_organizations_already_invited_to(self):
        user = self.login()
        invitation = MembershipRequest(kind="invitation", user=user)
        organization = OrganizationFactory(
            requests=[
                invitation,
                MembershipRequest(kind="invitation", email="new@example.com"),
            ]
        )

        self.get(self.change_email_link(user, "new@example.com"))

        organization.reload()
        assert [r.id for r in organization.requests] == [invitation.id]

    def test_change_mail_replaces_a_pending_request_by_the_email_invitation(self):
        """The invitation carries the role and assignments an admin chose, a request does not."""
        admin = UserFactory()
        user = self.login()
        invitation = MembershipRequest(
            kind="invitation", email="new@example.com", role="partial_editor"
        )
        organization = OrganizationFactory(
            members=[Member(user=admin, role="admin")],
            requests=[MembershipRequest(user=user, comment="Please add me"), invitation],
        )
        request_notification = MembershipRequestNotificationFactory(
            user=admin, request_organization=organization, request_user=user
        )

        self.get(self.change_email_link(user, "new@example.com"))

        organization.reload()
        assert [r.id for r in organization.requests] == [invitation.id]
        assert organization.requests[0].user == user
        assert organization.requests[0].role == "partial_editor"
        request_notification.reload()
        assert request_notification.handled_at is not None

    def test_change_mail_leaves_organizations_without_pending_invitation_to_the_address(self):
        """A canceled invitation and someone else's pending request are not a pending invitation."""
        user = self.login()
        organization = OrganizationFactory(
            requests=[
                MembershipRequest(kind="invitation", email="new@example.com", status="canceled"),
                MembershipRequest(user=UserFactory(), comment="Please add me"),
            ]
        )
        last_modified = organization.reload().last_modified

        self.get(self.change_email_link(user, "new@example.com"))

        assert organization.reload().last_modified == last_modified

    def test_change_mail(self):
        user = self.login(AdminFactory())

        new_email = "test@test.com"

        resp = self.get(self.change_email_link(user, new_email))
        assert resp.status_code == 302

        user.reload()
        assert user.email == new_email

    def test_change_mail_expired(self):
        """An expired link sends nothing: its owner asks again from their profile."""
        user = self.login(AdminFactory())
        original_email = user.email

        resp, mails = self.open_expired(self.change_email_link(user, "test@test.com"))

        assert resp.status_code == 302
        assert "change_email_expired" in resp.location
        assert mails == []
        assert user.reload().email == original_email

    def test_change_mail_expired_link_opened_by_someone_else(self):
        owner = UserFactory(email="owner@example.com")
        self.login(UserFactory(email="visitor@example.com"))

        resp, mails = self.open_expired(self.change_email_link(owner, "new@example.com"))

        assert "change_email_expired" in resp.location
        assert mails == []
        assert owner.reload().email == "owner@example.com"

    def test_change_mail_expired_link_opened_anonymously(self):
        owner = UserFactory(email="owner@example.com")

        resp, mails = self.open_expired(self.change_email_link(owner, "new@example.com"))

        assert "change_email_expired" in resp.location
        assert mails == []

    def test_change_mail_expired_link_of_a_user_not_found(self):
        """A password change rotates `fs_uniquifier`: the link no longer finds its owner."""
        owner = UserFactory(email="owner@example.com")
        link = self.change_email_link(owner, "new@example.com")
        current_app.extensions["security"].datastore.set_uniquifier(owner)

        resp, mails = self.open_expired(link)

        assert resp.status_code == 302
        assert mails == []

    def test_change_mail_already_taken(self):
        """Should not allow changing email to one already taken by another user"""
        user = self.login(AdminFactory())
        original_email = user.email

        # Create another user with the target email
        existing_user = UserFactory(email="taken@example.com")
        new_email = existing_user.email

        with capture_mails() as mails:
            resp = self.get(self.change_email_link(user, new_email))
        assert resp.status_code == 302
        assert "change_email_already_taken" in resp.location
        assert mails == []

        # Email should not have changed
        user.reload()
        assert user.email == original_email

    def test_change_mail_after_password_change(self):
        """Changing password rotates fs_uniquifier and invalidates email change token"""
        user = UserFactory(password="Password123")
        self.login(user)
        old_uniquifier = user.fs_uniquifier

        new_email = "new@example.com"

        confirmation_link = self.change_email_link(user, new_email)

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
