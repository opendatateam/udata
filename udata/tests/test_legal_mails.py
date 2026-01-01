import pytest
from flask import url_for

from udata.core.dataservices.factories import DataserviceFactory
from udata.core.dataset.factories import DatasetFactory
from udata.core.discussions.factories import DiscussionFactory, MessageDiscussionFactory
from udata.core.organization.factories import OrganizationFactory
from udata.core.reuse.factories import ReuseFactory
from udata.core.user.factories import AdminFactory, UserFactory
from udata.tests.api import APITestCase
from udata.tests.helpers import capture_mails


class AdminMailsOnDeleteTest(APITestCase):
    """Test admin mails are sent on delete when send_mail=True and user is sysadmin"""

    modules = []

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_dataset_delete_with_mail_as_admin(self):
        """Admin deleting dataset with send_mail=True should send email to owner"""
        self.login(AdminFactory())
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)

        with capture_mails() as mails:
            response = self.delete(url_for("api.dataset", dataset=dataset) + "?send_mail=true")

        self.assertStatus(response, 204)
        assert len(mails) == 1
        assert mails[0].recipients[0] == owner.email
        assert "deletion" in mails[0].subject.lower()

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_dataset_delete_without_mail_as_admin(self):
        """Admin deleting dataset without send_mail should not send email"""
        self.login(AdminFactory())
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)

        with capture_mails() as mails:
            response = self.delete(url_for("api.dataset", dataset=dataset))

        self.assertStatus(response, 204)
        assert len(mails) == 0

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_dataset_delete_with_mail_as_non_admin(self):
        """Non-admin deleting their dataset with send_mail=True should not send email"""
        owner = self.login()
        dataset = DatasetFactory(owner=owner)

        with capture_mails() as mails:
            response = self.delete(url_for("api.dataset", dataset=dataset) + "?send_mail=true")

        self.assertStatus(response, 204)
        assert len(mails) == 0

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_dataset_delete_with_org_owner_sends_to_admins(self):
        """Deleting org-owned dataset should send email to org admins"""
        self.login(AdminFactory())
        org_admin = UserFactory()
        org = OrganizationFactory(members=[{"user": org_admin, "role": "admin"}])
        dataset = DatasetFactory(organization=org)

        with capture_mails() as mails:
            response = self.delete(url_for("api.dataset", dataset=dataset) + "?send_mail=true")

        self.assertStatus(response, 204)
        assert len(mails) == 1
        assert mails[0].recipients[0] == org_admin.email

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_reuse_delete_with_mail_as_admin(self):
        """Admin deleting reuse with send_mail=True should send email to owner"""
        self.login(AdminFactory())
        owner = UserFactory()
        reuse = ReuseFactory(owner=owner)

        with capture_mails() as mails:
            response = self.delete(url_for("api.reuse", reuse=reuse) + "?send_mail=true")

        self.assertStatus(response, 204)
        assert len(mails) == 1
        assert mails[0].recipients[0] == owner.email

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_reuse_delete_without_mail_as_admin(self):
        """Admin deleting reuse without send_mail should not send email"""
        self.login(AdminFactory())
        owner = UserFactory()
        reuse = ReuseFactory(owner=owner)

        with capture_mails() as mails:
            response = self.delete(url_for("api.reuse", reuse=reuse))

        self.assertStatus(response, 204)
        assert len(mails) == 0

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_dataservice_delete_with_mail_as_admin(self):
        """Admin deleting dataservice with send_mail=True should send email to owner"""
        self.login(AdminFactory())
        owner = UserFactory()
        dataservice = DataserviceFactory(owner=owner)

        with capture_mails() as mails:
            response = self.delete(
                url_for("api.dataservice", dataservice=dataservice) + "?send_mail=true"
            )

        self.assertStatus(response, 204)
        assert len(mails) == 1
        assert mails[0].recipients[0] == owner.email

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_organization_delete_with_mail_as_admin(self):
        """Admin deleting organization with send_mail=True should send email to org admins"""
        self.login(AdminFactory())
        org_admin = UserFactory()
        org = OrganizationFactory(members=[{"user": org_admin, "role": "admin"}])

        with capture_mails() as mails:
            response = self.delete(url_for("api.organization", org=org) + "?send_mail=true")

        self.assertStatus(response, 204)
        assert len(mails) == 1
        assert mails[0].recipients[0] == org_admin.email

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_user_delete_with_mail_as_admin(self):
        """Admin deleting user with send_mail=True should send email to user"""
        self.login(AdminFactory())
        user_to_delete = UserFactory()

        with capture_mails() as mails:
            response = self.delete(url_for("api.user", user=user_to_delete) + "?send_mail=true")

        self.assertStatus(response, 204)
        assert len(mails) == 2  # 1 for admin mail + 1 for regular account deletion notification
        recipients = [m.recipients[0] for m in mails]
        assert user_to_delete.email in recipients

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_user_delete_with_mail_and_no_mail_as_admin(self):
        """Admin deleting user with send_mail=True and no_mail=True sends only admin mail"""
        self.login(AdminFactory())
        user_to_delete = UserFactory()

        with capture_mails() as mails:
            response = self.delete(
                url_for("api.user", user=user_to_delete) + "?send_mail=true&no_mail=true"
            )

        self.assertStatus(response, 204)
        assert len(mails) == 1  # Only admin mail, not regular account deletion notification
        assert mails[0].recipients[0] == user_to_delete.email

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_discussion_delete_with_mail_as_admin(self):
        """Admin deleting discussion with send_mail=True should send email to author"""
        self.login(AdminFactory())
        author = UserFactory()
        dataset = DatasetFactory()
        discussion = DiscussionFactory(subject=dataset, user=author)

        with capture_mails() as mails:
            response = self.delete(url_for("api.discussion", id=discussion.id) + "?send_mail=true")

        self.assertStatus(response, 204)
        assert len(mails) == 1
        assert mails[0].recipients[0] == author.email

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_message_delete_with_mail_as_admin(self):
        """Admin deleting message with send_mail=True should send email to author"""
        self.login(AdminFactory())
        author = UserFactory()
        message_author = UserFactory()
        dataset = DatasetFactory()
        discussion = DiscussionFactory(
            subject=dataset,
            user=author,
            discussion=[
                MessageDiscussionFactory(posted_by=author),
                MessageDiscussionFactory(posted_by=message_author),
            ],
        )

        with capture_mails() as mails:
            response = self.delete(
                url_for("api.discussion_comment", id=discussion.id, cidx=1) + "?send_mail=true"
            )

        self.assertStatus(response, 204)
        assert len(mails) == 1
        assert mails[0].recipients[0] == message_author.email

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_dataset_delete_without_owner_no_mail_sent(self):
        """Deleting dataset without owner or organization should not send email"""
        self.login(AdminFactory())
        dataset = DatasetFactory(owner=None, organization=None)

        with capture_mails() as mails:
            response = self.delete(url_for("api.dataset", dataset=dataset) + "?send_mail=true")

        self.assertStatus(response, 204)
        assert len(mails) == 0

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_reuse_delete_without_owner_no_mail_sent(self):
        """Deleting reuse without owner or organization should not send email"""
        self.login(AdminFactory())
        reuse = ReuseFactory(owner=None, organization=None)

        with capture_mails() as mails:
            response = self.delete(url_for("api.reuse", reuse=reuse) + "?send_mail=true")

        self.assertStatus(response, 204)
        assert len(mails) == 0

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_dataservice_delete_without_owner_no_mail_sent(self):
        """Deleting dataservice without owner or organization should not send email"""
        self.login(AdminFactory())
        dataservice = DataserviceFactory(owner=None, organization=None)

        with capture_mails() as mails:
            response = self.delete(
                url_for("api.dataservice", dataservice=dataservice) + "?send_mail=true"
            )

        self.assertStatus(response, 204)
        assert len(mails) == 0

    @pytest.mark.options(DEFAULT_LANGUAGE="en")
    def test_organization_delete_without_admins_no_mail_sent(self):
        """Deleting organization without admin members should not send email"""
        self.login(AdminFactory())
        editor = UserFactory()
        org = OrganizationFactory(members=[{"user": editor, "role": "editor"}])

        with capture_mails() as mails:
            response = self.delete(url_for("api.organization", org=org) + "?send_mail=true")

        self.assertStatus(response, 204)
        assert len(mails) == 0


class MailContentVariantsTest(APITestCase):
    """Test mail content varies based on settings"""

    modules = []

    @pytest.mark.options(
        DEFAULT_LANGUAGE="en",
        TERMS_OF_USE_URL="https://example.com/terms",
        TERMS_OF_USE_DELETION_ARTICLE="5.1.2",
        TELERECOURS_URL="https://telerecours.fr",
    )
    def test_mail_with_all_settings(self):
        """Mail should contain terms of use reference and telerecours when all settings defined"""
        self.login(AdminFactory())
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)

        with capture_mails() as mails:
            self.delete(url_for("api.dataset", dataset=dataset) + "?send_mail=true")

        assert len(mails) == 1
        body = mails[0].body
        assert "Our terms of use specify" in body
        assert "5.1.2" in body
        assert "Télérecours" in body

    @pytest.mark.options(
        DEFAULT_LANGUAGE="en",
        TERMS_OF_USE_DELETION_ARTICLE=None,
        TELERECOURS_URL=None,
    )
    def test_mail_without_settings(self):
        """Mail should use generic text when settings are not defined"""
        self.login(AdminFactory())
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)

        with capture_mails() as mails:
            self.delete(url_for("api.dataset", dataset=dataset) + "?send_mail=true")

        assert len(mails) == 1
        body = mails[0].body
        assert "Our terms of use specify" not in body
        assert "Télérecours" not in body
        assert "contacting us" in body

    @pytest.mark.options(
        DEFAULT_LANGUAGE="en",
        TERMS_OF_USE_URL="https://example.com/terms",
        TERMS_OF_USE_DELETION_ARTICLE="3.2",
        TELERECOURS_URL=None,
    )
    def test_mail_with_terms_only(self):
        """Mail should contain terms of use but generic appeal when only terms defined"""
        self.login(AdminFactory())
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)

        with capture_mails() as mails:
            self.delete(url_for("api.dataset", dataset=dataset) + "?send_mail=true")

        assert len(mails) == 1
        body = mails[0].body
        assert "Our terms of use specify" in body
        assert "3.2" in body
        assert "Télérecours" not in body
        assert "contacting us" in body

    @pytest.mark.options(
        DEFAULT_LANGUAGE="en",
        TERMS_OF_USE_DELETION_ARTICLE=None,
        TELERECOURS_URL="https://telerecours.fr",
    )
    def test_mail_with_telerecours_only(self):
        """Mail should contain telerecours but generic terms when only telerecours defined"""
        self.login(AdminFactory())
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)

        with capture_mails() as mails:
            self.delete(url_for("api.dataset", dataset=dataset) + "?send_mail=true")

        assert len(mails) == 1
        body = mails[0].body
        assert "Our terms of use specify" not in body
        assert "Télérecours" in body
        assert "contacting us" not in body

    @pytest.mark.options(
        DEFAULT_LANGUAGE="en",
        TERMS_OF_USE_URL=None,
        TERMS_OF_USE_DELETION_ARTICLE="5.1.2",
        TELERECOURS_URL=None,
    )
    def test_mail_with_article_but_no_url(self):
        """Mail should use generic terms when article is defined but URL is missing"""
        self.login(AdminFactory())
        owner = UserFactory()
        dataset = DatasetFactory(owner=owner)

        with capture_mails() as mails:
            self.delete(url_for("api.dataset", dataset=dataset) + "?send_mail=true")

        assert len(mails) == 1
        body = mails[0].body
        assert "Our terms of use specify" not in body
        assert "5.1.2" not in body
