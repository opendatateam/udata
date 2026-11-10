import logging
from copy import copy
from datetime import UTC, datetime, timedelta

from bson import ObjectId
from flask import current_app

from udata.api.oauth2 import OAuth2Token
from udata.core.api_token.models import ApiToken
from udata.tasks import job

from . import mails
from .models import User

log = logging.getLogger(__name__)


def users_acting_through_tokens_since(date: datetime) -> set[ObjectId]:
    """The users an API key or an OAuth2 token acted for since `date`: those requests aren't
    logins, `current_login_at` doesn't tell of them."""
    api_keys = ApiToken.objects(last_used_at__gt=date).no_dereference().distinct("user")
    oauth_tokens = OAuth2Token.objects(last_used_at__gt=date).no_dereference().distinct("user")
    return {*api_keys, *oauth_tokens}


@job("notify-inactive-users")
def notify_inactive_users(self):
    if not current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"]:
        logging.warning(
            "YEARS_OF_INACTIVITY_BEFORE_DELETION setting is not set, no deletion planned"
        )
        return
    notification_comparison_date = (
        datetime.now(UTC)
        - timedelta(days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"] * 365)
        + timedelta(days=current_app.config["DAYS_BEFORE_ACCOUNT_INACTIVITY_NOTIFY_DELAY"])
    )

    users_to_notify = User.objects(
        deleted=None,
        inactive_deletion_notified_at=None,
        current_login_at__lte=notification_comparison_date,
        id__nin=users_acting_through_tokens_since(notification_comparison_date),
    )
    for i, user in enumerate(users_to_notify):
        if i >= current_app.config["MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS"]:
            logging.warning("MAX_NUMBER_OF_USER_INACTIVITY_NOTIFICATIONS reached, stopping here.")
            return

        mails.inactive_user(user).send(user)

        logging.debug(f"Notified {user.email} of account inactivity")
        user.inactive_deletion_notified_at = datetime.now(UTC)
        user.save()

    logging.info(f"Notified {users_to_notify.count()} inactive users")


@job("delete-inactive-users")
def delete_inactive_users(self):
    if not current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"]:
        logging.warning(
            "YEARS_OF_INACTIVITY_BEFORE_DELETION setting is not set, no deletion planned"
        )
        return

    # Clear inactive_deletion_notified_at field if user has been active since notification
    for user in User.objects(deleted=None, inactive_deletion_notified_at__exists=True):
        notification = user.inactive_deletion_notified_at
        if user.current_login_at > notification or user.id in users_acting_through_tokens_since(
            notification
        ):
            user.inactive_deletion_notified_at = None
            user.save()

    # Delete inactive users upon notification delay if user still hasn't logged in
    deletion_comparison_date = datetime.now(UTC) - timedelta(
        days=current_app.config["YEARS_OF_INACTIVITY_BEFORE_DELETION"] * 365
    )
    notified_at = datetime.now(UTC) - timedelta(
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
