"""
We have our own system to build mails without Jinja templates with `MailMessage`.
To connect our system with the system from flask_security we need to override the Jinja
`render_template` function, create our MailMessage, and generate the HTML or text version.
`flask_security` then call the standard mail method from flask to send these strings.

In `render_mail_template` we support a few mails but not all. We could fallback to the regular
Jinja render function, but since we don't have any mails' templates defined in our application
the render function will crash, so we crash early in the `render_mail_template` function.

Note that `flask_security` have default templates for all mails but we create our own blueprint
specifying our `template` folder for templates and the system is not intelligent enough to try
our folder before fallbacking to the templates inside the `flask_security` package.
"""

import logging

from flask import current_app

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
            mail_message = welcome(**kwargs)
        case "welcome_existing":
            mail_message = welcome_existing(**kwargs)
        case "confirmation_instructions":
            mail_message = confirmation_instructions(**kwargs)
        case "reset_instructions":
            mail_message = reset_instructions(**kwargs)
        case "reset_notice":
            mail_message = reset_notice(**kwargs)
        case "change_notice":
            mail_message = change_notice(**kwargs)
        case _:
            raise Exception(f"Unknown mail message template: {name}")

    if format == "txt":
        return mail_message.text(kwargs.get("user"))
    elif format == "html":
        return mail_message.html(kwargs.get("user"))
    else:
        raise Exception(f"Mail message with unknown format: {name} (txt or html supported)")


def welcome(confirmation_link: str, **kwargs) -> MailMessage:
    from udata.i18n import lazy_gettext as _

    return MailMessage(
        subject=_("Confirm your email address"),
        paragraphs=[
            _("Welcome to %(site)s!", site=current_app.config["SITE_TITLE"]),
            _("Please confirm your email address."),
            MailCTA(_("Confirm your email address"), confirmation_link),
        ],
    )


def welcome_existing(recovery_link: str, **kwargs) -> MailMessage:
    from udata.i18n import lazy_gettext as _

    return MailMessage(
        subject=_("Your email address is already associated with an account"),
        paragraphs=[
            _(
                "Someone (you?) tried to create an account on %(site)s with your email.",
                site=current_app.config["SITE_TITLE"],
            ),
            _("If you forgot your password, you can reset it."),
            MailCTA(_("Reset your password"), recovery_link),
        ],
    )


def confirmation_instructions(confirmation_link: str, **kwargs) -> MailMessage:
    from udata.i18n import lazy_gettext as _

    return MailMessage(
        subject=_("Confirm your email address"),
        paragraphs=[
            _("Please confirm your email address."),
            MailCTA(_("Confirm your email address"), confirmation_link),
        ],
    )


def reset_instructions(reset_token: str, **kwargs) -> MailMessage:
    from udata.i18n import lazy_gettext as _
    from udata.uris import cdata_url

    return MailMessage(
        subject=_("Reset your password"),
        paragraphs=[
            _(
                "Someone requested a password reset for your %(site)s account.",
                site=current_app.config["SITE_TITLE"],
            ),
            _("If this wasn't you, please ignore this email."),
            MailCTA(_("Reset your password"), cdata_url(f"/reset/{reset_token}")),
        ],
    )


def reset_notice(**kwargs) -> MailMessage:
    from udata.i18n import lazy_gettext as _

    return MailMessage(
        subject=_("Your password has been reset"),
        paragraphs=[
            _("Your data.gouv.fr password has been reset."),
        ],
    )


def change_notice(**kwargs) -> MailMessage:
    from udata.i18n import lazy_gettext as _
    from udata.uris import cdata_url

    return MailMessage(
        subject=_("Your password has been changed"),
        paragraphs=[
            _(
                "Your %(site)s account password has been changed.",
                site=current_app.config["SITE_TITLE"],
            ),
            _("If you did not change your password, please reset it."),
            MailCTA(_("Reset your password"), cdata_url("/reset/")),
        ],
    )
