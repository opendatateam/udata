import logging
import typing as t

from flask import current_app
from flask_security import signals
from flask_security.mail_util import MailUtil
from flask_security.utils import url_for_security

from udata.i18n import lazy_gettext as _
from udata.mail import MailCTA, MailMessage

log = logging.getLogger(__name__)


def user_registered(confirmation_token: str, **kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Confirmez votre adresse email"),
        paragraphs=[
            _("Bienvenue sur %(site)s !", site=current_app.config["SITE_TITLE"]),
            _("Veuillez confirmer votre adresse email."),
            MailCTA(
                _("Confirmer votre adresse email"),
                url_for_security("confirm_email", token=confirmation_token, _external=True),
            ),
        ],
    )


def user_not_registered(**kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Votre adresse email est déjà associée à un compte"),
        paragraphs=[
            _(
                "Quelqu’un (vous ?) a essayé de créer un compte sur %(site)s avec votre email.",
                site=current_app.config["SITE_TITLE"],
            ),
            _("Si vous avez oublié votre mot de passe, vous pouvez le réinitialiser."),
            MailCTA(
                _("Réinitialiser votre mot de passe"),
                url_for_security("forgot_password", _external=True),
            ),
        ],
    )


def confirm_instructions_sent(confirmation_token: str, **kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Confirmez votre adresse email"),
        paragraphs=[
            _("Veuillez confirmer votre adresse email."),
            MailCTA(
                _("Confirmer votre adresse email"),
                url_for_security("confirm_email", token=confirmation_token, _external=True),
            ),
        ],
    )


def reset_password_instructions_sent(reset_token: str, **kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Réinitialisez votre mot de passe"),
        paragraphs=[
            _(
                "Quelqu’un a demandé une réinitialisation du mot de passe de votre compte %(site)s.",
                site=current_app.config["SITE_TITLE"],
            ),
            _("Si ce n’est pas vous, veuillez ignorer cet email."),
            MailCTA(
                _("Réinitialisez votre mot de passe"),
                url_for_security("reset_password", token=reset_token, _external=True),
            ),
        ],
    )


def password_reset(**kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Votre mot de passe a bien été réinitialisé"),
        paragraphs=[
            _("Votre mot de passe data.gouv.fr a été réinitialisé."),
        ],
    )


def password_changed(reset_token: str, **kwargs) -> MailMessage:
    return MailMessage(
        subject=_("Votre mot de passe a été modifié"),
        paragraphs=[
            _(
                "Le mot de passe de votre compte %(site)s a été modifié.",
                site=current_app.config["SITE_TITLE"],
            ),
            _("Si vous n’avez pas modifié votre mot de passe veuillez le réinitialiser."),
            MailCTA(
                _("Réinitialisez votre mot de passe"),
                url_for_security("reset_password", _external=True),
            ),
        ],
    )


mails_to_signals = {
    # Mails we want to manage
    "welcome": (signals.user_registered, user_registered),
    "welcome_existing": (signals.user_not_registered, user_not_registered),
    "confirmation_instructions": (signals.confirm_instructions_sent, confirm_instructions_sent),
    "reset_instructions": (
        signals.reset_password_instructions_sent,
        reset_password_instructions_sent,
    ),
    "reset_notice": (signals.password_reset, password_reset),
    "change_notice": (signals.password_changed, password_changed),
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
