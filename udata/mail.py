import copy
import logging
from dataclasses import dataclass

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
    content: str | None
    inlined: bool = False


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
                    f'<a href="{value.url_for(_mailCampaign=True)}">{str(value)}</a>'
                )

        return str(new_paragraph)


@dataclass
class MailMessage:
    subject: LazyString
    paragraphs: list[LazyString | MailCTA | ParagraphWithLinks | LabelledContent]

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


def init_app(app):
    mail.init_app(app)


def send_mail(recipients: object | list, message: MailMessage):
    debug = current_app.config.get("DEBUG", False)
    send_mail = current_app.config.get("SEND_MAIL", not debug)

    if not isinstance(recipients, list):
        recipients = [recipients]

    for recipient in recipients:
        lang = i18n._default_lang(recipient)
        with i18n.language(lang):
            msg = Message(
                subject=str(message.subject),
                body=message.text(recipient),
                html=message.html(recipient),
                recipients=[recipient.email],
            )

        if send_mail:
            with mail.connect() as conn:
                conn.send(msg)
        else:
            log.debug(f"Sending mail {message.subject} to {recipient.email}")
            log.debug(msg.body)
            log.debug(msg.html)
            mail_sent.send(msg)


# def send(subject, recipients, template_base, **kwargs):
#     """
#     Send a given email to multiple recipients.

#     User prefered language is taken in account.
#     To translate the subject in the right language, you should ugettext_lazy
#     """
#     sender = kwargs.pop("sender", None)
#     if not isinstance(recipients, (list, tuple)):
#         recipients = [recipients]

#     tpl_path = f"mail/{template_base}"

#     debug = current_app.config.get("DEBUG", False)
#     send_mail = current_app.config.get("SEND_MAIL", not debug)
#     connection = mail.connect if send_mail else dummyconnection
#     extras = get_mail_campaign_dict()

#     with connection() as conn:
#         for recipient in recipients:
#             lang = i18n._default_lang(recipient)
#             with i18n.language(lang):
#                 log.debug('Sending mail "%s" to recipient "%s"', subject, recipient)
#                 msg = Message(subject, sender=sender, recipients=[recipient.email])
#                 msg.body = render_template(
#                     f"{tpl_path}.txt",
#                     subject=subject,
#                     sender=sender,
#                     recipient=recipient,
#                     extras=extras,
#                     **kwargs,
#                 )
#                 msg.html = render_template(
#                     f"{tpl_path}.html",
#                     subject=subject,
#                     sender=sender,
#                     recipient=recipient,
#                     extras=extras,
#                     **kwargs,
#                 )
#                 try:
#                     conn.send(msg)
#                 except SMTPException as e:
#                     log.error(f"Error sending mail {e}")


def get_mail_campaign_dict() -> dict:
    """Return a dict with the `mtm_campaign` key set if there is a `MAIL_CAMPAIGN` configured in udata.cfg."""
    extras = {}
    mail_campaign = current_app.config.get("MAIL_CAMPAIGN")
    if mail_campaign:
        extras["mtm_campaign"] = mail_campaign
    return extras
