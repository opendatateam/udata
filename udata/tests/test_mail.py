from contextlib import contextmanager
from smtplib import SMTPRecipientsRefused

import pytest

from udata.core.user.factories import UserFactory
from udata.mail import mail_sent, send
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
