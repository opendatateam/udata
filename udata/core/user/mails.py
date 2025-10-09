from flask import current_app

from udata.i18n import lazy_gettext as _
from udata.mail import MailCTA, MailMessage
from udata.uris import homepage_url


def account_deletion() -> MailMessage:
    return MailMessage(
        subject=_("Account deletion"),
        paragraphs=[_("Your account has now been deleted")],
    )


def inactive_account_deleted() -> MailMessage:
    return MailMessage(
        subject=_(
            "Deletion of your inactive %(site)s account", site=current_app.config["SITE_TITLE"]
        ),
        paragraphs=[
            _(
                "Your account on %(site)s has been deleted due to inactivity",
                site=current_app.config["SITE_TITLE"],
            )
        ],
    )


def inactive_user(user) -> MailMessage:
    config = current_app.config

    return MailMessage(
        subject=_("Inactivity of your {site} account").format(site=config["SITE_TITLE"]),
        paragraphs=[
            _(
                "We have noticed that your account associated to (%(user_email)s) has been inactive for %(inactivity_years)d years or more on %(site)s, the open platform for public data.",
                user_email=user.email,
                inactivity_years=config["YEARS_OF_INACTIVITY_BEFORE_DELETION"],
                site=config["SITE_TITLE"],
            ),
            MailCTA(
                label=_("If you want to keep your account, please log in with your account."),
                link=homepage_url(),
            ),
            _(
                "Without logging in, your account will be deleted within %(notify_delay)d days.",
                notify_delay=config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"],
            ),
            _(
                "This account is not tied to your other administration accounts and you can always re-create an account on the %(site)s platform if necessary.",
                site=config["SITE_TITLE"],
            ),
        ],
    )
