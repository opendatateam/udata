import logging
from datetime import UTC, datetime, timedelta

from flask import current_app

from udata import i18n
from udata.features.notifications import mails
from udata.features.notifications.constants import MailCadence
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

    There is no cursor to keep: a notification still `mail_pending` is one that has
    not been mailed, and the oldest of them says when the wait started. A missed run
    is therefore caught by the next one, and running twice sends nothing twice.

    Schedule it hourly, not at the pace of a cadence: a notification that arrives just
    after a daily run is not due at the next one, and would wait almost two days. Run
    every hour, a digest leaves at most an hour after its cadence is up.
    """
    sent = 0
    # Only users with something waiting, which is a small set: an immediate recipient
    # never queues anything.
    for user in Notification.objects(mail_pending=True).distinct("user"):
        if user is None or user.deleted:
            continue

        # What was queued before the pause stays in the bell, but is not mailed: neither
        # now, nor in one go on resuming.
        if user.notifications_paused:
            Notification.objects(user=user, mail_pending=True).update(
                set__mail_pending=False, set__last_modified=datetime.now(UTC)
            )
            continue

        due_before = datetime.now(UTC) - DIGEST_INTERVALS[user.mail_cadence]
        # What was answered or read in the meantime is no news any more.
        queue = Notification.objects(user=user, mail_pending=True, handled_at=None)
        if not queue.filter(created_at__lte=due_before).first():
            continue

        # The whole queue goes out, not only the part that came of age: a digest is
        # "what happened since last time", and holding back the recent half would only
        # push it to the next run.
        notifications = list(queue.order_by("created_at"))
        # The counts are rendered while the digest is built, before `send` switches to the
        # recipient's language. Outside the `try`: `i18n.language` restores nothing when
        # an exception goes through it.
        with i18n.language(i18n._default_lang(user)):
            # One failing digest must not deprive the others. Its queue is left as is, so
            # the next run tries again.
            try:
                digest = mails.notification_digest(notifications)
                if digest is not None:
                    digest.send(user)
                    sent += 1
            except Exception:
                log.exception(f"Could not send the notification digest of {user}")
                continue

        # Only what was mailed is spent: a notification arriving meanwhile stays queued.
        # `last_modified` is set by hand, a queryset update skips the `pre_save` filling it.
        mailed = Notification.objects(id__in=[notification.id for notification in notifications])
        mailed.update(set__mail_pending=False, set__last_modified=datetime.now(UTC))

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
