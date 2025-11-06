import logging
from copy import copy
from datetime import datetime, timedelta

from flask import current_app

from udata.tasks import job

from . import mails
from .models import User

log = logging.getLogger(__name__)


@job("notify-inactive-users")
def notify_inactive_users(self):
    if not current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"]:
        logging.warning(
            "YEARS_OF_INACTIVITY_BEFORE_DELETION setting is not set, no deletion planned"
        )
        return
    notification_comparison_date = (
        datetime.utcnow()
        - timedelta(days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"] * 365)
        + timedelta(days=current_app.config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"])
    )

    users_to_notify = User.objects(
        deleted=None,
        inactive_deletion_notified_at=None,
        current_login_at__lte=notification_comparison_date,
    )
    for i, user in enumerate(users_to_notify):
        if i >= current_app.config["MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS"]:
            logging.warning("MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS reached, stopping here.")
            return

        mails.inactive_user(user).send(user)

        logging.debug(f"Notified {user.email} of account inactivity")
        user.inactive_deletion_notified_at = datetime.utcnow()
        user.save()

    logging.info(f"Notified {users_to_notify.count()} inactive users")


@job("delete-inactive-users")
def delete_inactive_users(self):
    if not current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"]:
        logging.warning(
            "YEARS_OF_INACTIVITY_BEFORE_DELETION setting is not set, no deletion planned"
        )
        return

    # Clear inactive_deletion_notified_at field if user has logged in since notification
    for user in User.objects(deleted=None, inactive_deletion_notified_at__exists=True):
        if user.current_login_at > user.inactive_deletion_notified_at:
            user.inactive_deletion_notified_at = None
            user.save()

    # Delete inactive users upon notification delay if user still hasn't logged in
    deletion_comparison_date = datetime.utcnow() - timedelta(
        days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"] * 365
    )
    notified_at = datetime.utcnow() - timedelta(
        days=current_app.config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"]
    )
    users_to_delete = User.objects(
        deleted=None,
        current_login_at__lte=deletion_comparison_date,
        inactive_deletion_notified_at__lte=notified_at,
    )
    for user in users_to_delete:
        copied_user = copy(user)
        user.mark_as_deleted(notify=False, delete_comments=False)
        logging.warning(f"Deleted user {copied_user.email} due to account inactivity")
        mails.inactive_account_deleted().send(copied_user)

    logging.info(f"Deleted {users_to_delete.count()} inactive users")
