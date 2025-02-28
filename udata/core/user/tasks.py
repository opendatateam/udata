import logging
from copy import copy
from datetime import datetime, timedelta

from flask import current_app

from udata import mail
from udata.i18n import lazy_gettext as _
from udata.tasks import job, task

from .models import User, datastore

log = logging.getLogger(__name__)


@task(route="high.mail")
def send_test_mail(email):
    user = datastore.find_user(email=email)
    mail.send(_("Test mail"), user, "test")


@job("notify-inactive-users")
def notify_inactive_users(self):
    if not current_app.config["YEARS_OF_INACTIVITY_BEFORE_DEACTIVATION"]:
        logging.warning(
            "YEARS_OF_INACTIVITY_BEFORE_DEACTIVATION setting is not set, no deletion planned"
        )
        return
    notification_comparison_date = (
        datetime.utcnow()
        - timedelta(days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DEACTIVATION"] * 365)
        + timedelta(days=current_app.config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"])
    )

    for i, user in enumerate(
        User.objects(
            deleted=None,
            inactive_deletion_notified_at=None,
            current_login_at__lte=notification_comparison_date,
        )
    ):
        if i >= current_app.config["MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS"]:
            logging.warning("MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS reached, stopping here.")
            return
        mail.send(
            _("Inactivity of your {site} account").format(site=current_app.config["SITE_TITLE"]),
            user,
            "account_inactivity",
            user=user,
        )
        user.inactive_deletion_notified_at = datetime.utcnow()
        user.save()


@job("delete-inactive-users")
def delete_inactive_users(self):
    if not current_app.config["YEARS_OF_INACTIVITY_BEFORE_DEACTIVATION"]:
        logging.warning(
            "YEARS_OF_INACTIVITY_BEFORE_DEACTIVATION setting is not set, no deletion planned"
        )
        return

    # Clear inactive_deletion_notified_at field if user has logged in since notification
    for user in User.objects(deleted=None, inactive_deletion_notified_at__exists=True):
        if user.current_login_at > user.inactive_deletion_notified_at:
            user.inactive_deletion_notified_at = None
            user.save()

    # Delete inactive users upon notification delay if user still hasn't logged in
    deletion_comparison_date = datetime.utcnow() - timedelta(
        days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DEACTIVATION"] * 365
    )
    notified_at = datetime.utcnow() - timedelta(
        days=current_app.config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"]
    )
    for user in User.objects(
        deleted=None,
        current_login_at__lte=deletion_comparison_date,
        inactive_deletion_notified_at__lte=notified_at,
    ):
        copied_user = copy(user)
        user.mark_as_deleted(notify=False, delete_comments=False)
        mail.send(
            _("Deletion of your inactive {site} account").format(
                site=current_app.config["SITE_TITLE"]
            ),
            copied_user,
            "inactive_account_deleted",
        )
