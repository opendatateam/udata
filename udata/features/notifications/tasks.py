import logging
from datetime import UTC, datetime, timedelta

from flask import current_app

from udata.features.notifications import mails
from udata.features.notifications.constants import MailCadence, NotificationChannel
from udata.features.notifications.models import Notification
from udata.tasks import job

log = logging.getLogger(__name__)

# How long a cadence waits before its next mail. `IMMEDIATE` is in there on purpose:
# somebody who switches back to immediate would otherwise keep a queue no job ever
# comes for.
DIGEST_INTERVALS = {
    MailCadence.IMMEDIATE: timedelta(0),
    MailCadence.DAILY: timedelta(days=1),
    MailCadence.WEEKLY: timedelta(weeks=1),
}


@job("send-notification-digests")
def send_notification_digests(self):
    """Mail everyone whose pending notifications have waited out their cadence.

    There is no cursor to keep: a notification still holding `MAIL` is one that has
    not been mailed, and the oldest of them says when the wait started. A missed run
    is therefore caught by the next one, and running twice sends nothing twice.
    """
    sent = 0
    # Only users with something waiting, which is a small set: an immediate recipient
    # never queues anything.
    for user in Notification.objects(channels=NotificationChannel.MAIL).distinct("user"):
        if user is None or user.deleted:
            continue

        due_before = datetime.now(UTC) - DIGEST_INTERVALS[user.mail_cadence]
        if not Notification.objects(
            user=user, channels=NotificationChannel.MAIL, created_at__lte=due_before
        ).first():
            continue

        # The whole queue goes out, not only the part that came of age: a digest is
        # "what happened since last time", and holding back the recent half would only
        # push it to the next run.
        notifications = list(
            Notification.objects(user=user, channels=NotificationChannel.MAIL).order_by(
                "created_at"
            )
        )
        message = mails.notification_digest(notifications)
        if message is not None:
            message.send(user)
            sent += 1

        for notification in notifications:
            notification.channels = [
                channel
                for channel in notification.channels
                if channel is not NotificationChannel.MAIL
            ]
            if notification.channels:
                notification.save()
            else:
                # Nothing left to deliver it through, and it was never meant to be read
                # in the bell.
                notification.delete()

    log.info(f"Sent {sent} notification digests")


@job("delete-expired-notifications")
def delete_expired_notifications(self):
    # Delete expired notifications
    handled_at = datetime.now(UTC) - timedelta(
        days=current_app.config["DAYS_AFTER_NOTIFICATION_EXPIRED"]
    )
    notifications_to_delete = Notification.objects(
        handled_at__lte=handled_at,
    )
    count = notifications_to_delete.count()
    for notification in notifications_to_delete:
        notification.delete()

    log.info(f"Deleted {count} expired notifications")
