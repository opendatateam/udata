from contextlib import contextmanager
from smtplib import SMTPRecipientsRefused

import pytest

from udata.core.organization.factories import OrganizationFactory
from udata.core.user.factories import UserFactory
from udata.mail import mail, mail_sent, send
from udata.tests import DBTestMixin, TestCase
from udata.tests.helpers import assert_emit, assert_not_emit

SMTPRecipientsRefusedList = ["not-found@udata", "not-found-either@udata"]


class FakeSender:
    def send(self, msg):
        if all(recipient in SMTPRecipientsRefusedList for recipient in msg.recipients):
            raise SMTPRecipientsRefused(msg.recipients)
        mail_sent.send(msg)


class FakeMail:
    @contextmanager
    def connect(*args, **kw):
        yield FakeSender()


class MailSendTest(TestCase, DBTestMixin):
    def create_app(self):
        app = super().create_app()
        app.config["SEND_MAIL"] = True
        return app

    @pytest.fixture(autouse=True)
    def patch_mail(self, mocker):
        mocker.patch("udata.mail.mail", FakeMail())

    def test_send_mail(self):
        with assert_emit(mail_sent):
            send("subject", [UserFactory(email="recipient@udata")], "base")

    def test_send_mail_to_not_found_recipients(self):
        with assert_not_emit(mail_sent):
            send("subject", [UserFactory(email="not-found@udata")], "base")

    def test_send_mail_to_multiple_recipients_with_some_not_found(self):
        recipients = [
            UserFactory(email="not-found@udata"),
            UserFactory(email="recipient@udata"),
            UserFactory(email="not-found-either@udata"),
        ]
        with assert_emit(mail_sent):
            send("subject", recipients, "base")


@pytest.mark.usefixtures("clean_db")
@pytest.mark.frontend
class MailCampaignTest:
    def test_send_mail_campaign_link_new_member(self, app):
        # MTM campaign are only added on web URL (not API ones generated when
        # no front-end is configured)
        app.config["CDATA_BASE_URL"] = "https://www.data.gouv.fr"

        org = OrganizationFactory()
        recipient = UserFactory(email="recipient@udata")

        app.config["SEND_MAIL"] = True
        app.config["MAIL_CAMPAIGN"] = ""
        with mail.record_messages() as outbox:
            send(
                "subject",
                [recipient],
                "new_member",
                org=org,
            )
        assert len(outbox) == 1
        message = outbox[0]
        assert "mtm_campaign" not in message.body
        assert "mtm_campaign" not in message.html

        app.config["MAIL_CAMPAIGN"] = "data-gouv-fr"
        with mail.record_messages() as outbox:
            send(
                "subject",
                [recipient],
                "new_member",
                org=org,
            )
        assert len(outbox) == 1
        message = outbox[0]
        assert "mtm_campaign=data-gouv-fr" in message.body
        assert "mtm_campaign=data-gouv-fr" in message.html

    def test_send_mail_campaign_link_badge_added_company(self, app):
        # MTM campaign are only added on web URL (not API ones generated when
        # no front-end is configured)
        app.config["CDATA_BASE_URL"] = "https://www.data.gouv.fr"

        app.config["SEND_MAIL"] = True
        org = OrganizationFactory()
        org.add_badge("company")
        badge = org.badges[0]
        badge.created_by = UserFactory()
        recipient = UserFactory(email="recipient@udata")

        app.config["MAIL_CAMPAIGN"] = ""
        with mail.record_messages() as outbox:
            send("subject", [recipient], "badge_added_company", organization=org, badge=badge)
        assert len(outbox) == 1
        message = outbox[0]
        assert "mtm_campaign" not in message.body
        assert "mtm_campaign" not in message.html

        app.config["MAIL_CAMPAIGN"] = "data-gouv-fr"
        with mail.record_messages() as outbox:
            send("subject", [recipient], "badge_added_company", organization=org, badge=badge)
        assert len(outbox) == 1
        message = outbox[0]
        assert "mtm_campaign=data-gouv-fr" in message.body
        assert "mtm_campaign=data-gouv-fr" in message.html
