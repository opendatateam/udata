import logging

from flask import current_app
from flask_security.utils import url_for_security

from udata.i18n import lazy_gettext as _
from udata.mail import MailCTA, MailMessage

log = logging.getLogger(__name__)


def render_mail_template(template_name_or_list: str | list[str], **kwargs):
    if not isinstance(template_name_or_list, str):
        return None

    if not template_name_or_list.startswith("security/email/"):
        return None

    if not template_name_or_list.endswith(".txt") and not template_name_or_list.endswith(".html"):
        return None

    (name, format) = template_name_or_list.removeprefix("security/email/").split(".")

    mail_message = None
    match name:
        case "welcome":
            mail_message = welcome(kwargs.get("confirmation_token"))
        case "welcome_existing":
            mail_message = welcome_existing()
        case "confirmation_instructions":
            mail_message = confirmation_instructions(kwargs.get("confirmation_link"))
        case "reset_instructions":
            mail_message = reset_instructions(kwargs.get("reset_token"))
        case "reset_notice":
            mail_message = reset_notice()
        case "change_notice":
            mail_message = change_notice()
        case _:
            log.error(f"Unknown mail message template: {name}")
            return None

    if format == "txt":
        return mail_message.text(kwargs.get("user"))
    elif format == "html":
        return mail_message.html(kwargs.get("user"))
    else:
        log.error(f"Mail message with unknown format: {name} (txt or html supported)")

    return None


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


def confirmation_instructions(confirmation_link: str, **kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Confirm your email address"),
        paragraphs=[
            _("Please confirm your email address."),
            MailCTA(_("Confirm your email address"), confirmation_link),
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


def change_notice(**kwargs) -> MailMessage:
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
