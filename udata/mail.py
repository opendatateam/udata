import copy
import logging
from dataclasses import dataclass
from html import escape

from blinker import signal
from flask import current_app, render_template
from flask_babel import LazyString
from flask_mail import Mail, Message

from udata import i18n

log = logging.getLogger(__name__)

mail = Mail()

mail_sent = signal("mail-sent")


@dataclass
class MailCTA:
    label: LazyString
    link: str | None


@dataclass
class LabelledContent:
    label: LazyString
    content: str
    inline: bool = False
    truncated_at: int = 50

    @property
    def truncated_content(self) -> str:
        return (
            self.content[: self.truncated_at] + "…"
            if len(self.content) > self.truncated_at
            else self.content
        )


@dataclass
class ParagraphWithLinks:
    paragraph: LazyString

    def __str__(self):
        return str(self.paragraph)

    @property
    def html(self):
        new_paragraph = copy.deepcopy(self.paragraph)

        for key, value in new_paragraph._kwargs.items():
            if hasattr(value, "url_for"):
                new_paragraph._kwargs[key] = (
                    f'<a href="{value.url_for(_mailCampaign=True)}" style="color: #000000; text-decoration: underline;">{escape(str(value))}</a>'
                )

        return str(new_paragraph)


@dataclass
class MailMessage:
    subject: LazyString
    paragraphs: list[LazyString | MailCTA | ParagraphWithLinks | LabelledContent | None]

    def __post_init__(self):
        self.paragraphs = [p for p in self.paragraphs if p is not None]

    def text(self, recipient) -> str:
        return render_template(
            "mail/message.txt",
            message=self,
            recipient=recipient,
        )

    def html(self, recipient) -> str:
        return render_template(
            "mail/message.html",
            message=self,
            recipient=recipient,
        )

    def send(self, recipients):
        send_mail(recipients, self)


def init_app(app):
    mail.init_app(app)


def send_mail(recipients: object | list, message: MailMessage):
    debug = current_app.config.get("DEBUG", False)
    send_mail = current_app.config.get("SEND_MAIL", not debug)

    if not isinstance(recipients, list):
        recipients = [recipients]

    for recipient in recipients:
        lang = i18n._default_lang(recipient)
        to = recipient if isinstance(recipient, str) else recipient.email
        with i18n.language(lang):
            msg = Message(
                subject=str(message.subject),
                body=message.text(recipient),
                html=message.html(recipient),
                recipients=[to],
            )

        if send_mail:
            with mail.connect() as conn:
                conn.send(msg)
        else:
            log.debug(f"Sending mail {message.subject} to {to}")
            log.debug(msg.body)
            log.debug(msg.html)
            mail_sent.send(msg)


def get_mail_campaign_dict() -> dict:
    """Return a dict with the `mtm_campaign` key set if there is a `MAIL_CAMPAIGN` configured in udata.cfg."""
    extras = {}
    mail_campaign = current_app.config.get("MAIL_CAMPAIGN")
    if mail_campaign:
        extras["mtm_campaign"] = mail_campaign
    return extras
