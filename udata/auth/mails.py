import logging
import typing as t

from flask import current_app, url_for
from flask_security import signals
from flask_security.mail_util import MailUtil
from flask_security.utils import url_for_security

from udata.i18n import lazy_gettext as _
from udata.mail import MailCTA, MailMessage

log = logging.getLogger(__name__)


def welcome(confirmation_token: str, **kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Confirm your email address"),
        paragraphs=[
            _("Welcome to %(site)s!", site=current_app.config["SITE_TITLE"]),
            _("Please confirm your email address."),
            MailCTA(
                _("Confirm your email address"),
                url_for_security("confirm_email", token=confirmation_token, _external=True),
            ),
        ],
    )


def welcome_existing(**kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Your email address is already associated with an account"),
        paragraphs=[
            _(
                "Someone (you?) tried to create an account on %(site)s with your email.",
                site=current_app.config["SITE_TITLE"],
            ),
            _("If you forgot your password, you can reset it."),
            MailCTA(
                _("Reset your password"),
                url_for_security("forgot_password", _external=True),
            ),
        ],
    )


def confirmation_instructions(confirmation_token: str, **kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Confirm your email address"),
        paragraphs=[
            _("Please confirm your email address."),
            MailCTA(
                _("Confirm your email address"),
                url_for("security.confirm_change_email", token=confirmation_token, _external=True),
            ),
        ],
    )


def reset_instructions(reset_token: str, **kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Reset your password"),
        paragraphs=[
            _(
                "Someone requested a password reset for your %(site)s account.",
                site=current_app.config["SITE_TITLE"],
            ),
            _("If this wasn't you, please ignore this email."),
            MailCTA(
                _("Reset your password"),
                url_for_security("reset_password", token=reset_token, _external=True),
            ),
        ],
    )


def reset_notice(**kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Your password has been reset"),
        paragraphs=[
            _("Your data.gouv.fr password has been reset."),
        ],
    )


def change_notice(reset_token: str, **kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Your password has been changed"),
        paragraphs=[
            _(
                "Your %(site)s account password has been changed.",
                site=current_app.config["SITE_TITLE"],
            ),
            _("If you did not change your password, please reset it."),
            MailCTA(
                _("Reset your password"),
                url_for_security("reset_password", _external=True),
            ),
        ],
    )


mails_to_signals = {
    # Mails we want to manage
    "welcome": (signals.user_registered, welcome),
    "welcome_existing": (signals.user_not_registered, welcome_existing),
    "confirmation_instructions": (signals.confirm_instructions_sent, confirmation_instructions),
    "reset_instructions": (
        signals.reset_password_instructions_sent,
        reset_instructions,
    ),
    "reset_notice": (signals.password_reset, reset_notice),
    "change_notice": (signals.password_changed, change_notice),
    # Other mails
    "login_instructions": None,
    "two_factor_instructions": None,
    "two_factor_rescue": None,
    "us_instructions": None,
    "welcome_existing_username": None,
}


class UdataMailUtil(MailUtil):
    def send_mail(
        self,
        template: str,
        subject: str,
        recipient: str,
        sender: t.Union[str, tuple],
        body: str,
        html: t.Optional[str],
        **kwargs: t.Any,
    ) -> None:
        # We want to use our mail system but here, we just have the rendered
        # templates and not raw informations, so we need to disable sending
        # these mails here and do it via the signals (which have all the raw
        # informations)
        if template in mails_to_signals and mails_to_signals[template] is not None:
            return

        if template in mails_to_signals:
            # These mails should never be sent by our system because we don't use
            # there Flask-Security features. But in any case we activate them, send
            # the default mail and log a warning.
            log.warning(
                f"Mail template '{template}' is disabled but was triggered. "
                f"Sending default Flask-Security mail to {recipient}"
            )
        else:
            # These mails are unkwown, we better look into it and add them either to our
            # supported emails or to the None list…
            log.error(
                f"Unknown mail template '{template}' was triggered for {recipient}. "
                f"Please add it to mails_to_signals."
            )

        return super().send_mail(template, subject, recipient, sender, body, html, **kwargs)


def create_signal_handler(mail_function):
    """Factory function to create signal handlers for each mail template."""

    def handler(sender, *args, **kwargs):
        mail_function(*args, **kwargs).send(kwargs.get("user"))

    return handler


# Register signal handlers for all managed mails
for signal_info in mails_to_signals.values():
    if signal_info is not None:
        signal_info[0].connect(create_signal_handler(signal_info[1]))
