import logging
from collections import Counter
from datetime import UTC, datetime, timedelta

from flask import current_app
from mongoengine import DoesNotExist

from udata import i18n
from udata.features.notifications.constants import MailCadence, NotificationType
from udata.features.notifications.events import event_for_type
from udata.features.notifications.mails import settings_footer
from udata.features.notifications.models import Notification
from udata.i18n import lazy_gettext as _
from udata.i18n import lazy_ngettext
from udata.mail import Link, MailMessage, ParagraphWithLinks
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


def notification_digest(notifications: list[Notification]) -> MailMessage | None:
    """What happened since the last digest, `None` when nothing of it is left to tell.

    One line per subject rather than one per notification, because a busy thread would
    otherwise fill the mail with the same title repeated. Each event says what its line
    is about and how it counts (`digest_subject`, `digest_count`).

    A notification whose subject is gone (a post deleted with its discussions left
    behind) is left out: failing on it would hold back the whole digest, run after run.
    """
    # Insertion order keeps the oldest subject first, which is the order the queue was
    # read in.
    links: dict[object, Link] = {}
    counts: dict[object, Counter[NotificationType]] = {}
    for notification in notifications:
        try:
            key, link = event_for_type(notification.type).digest_subject(notification.details)
        except DoesNotExist:
            continue
        links.setdefault(key, link)
        counts.setdefault(key, Counter())[notification.type] += 1
    if not counts:
        return None

    lines = [
        ParagraphWithLinks(
            _(
                "%(subject)s: %(counts)s",
                subject=links[key],
                counts=", ".join(
                    event_for_type(type).digest_count(count) for type, count in by_type.items()
                ),
            )
        )
        for key, by_type in counts.items()
    ]

    return MailMessage(
        subject=lazy_ngettext(
            "Updates on an item you follow",
            "Updates on %(num)d items you follow",
            len(lines),
        ),
        paragraphs=[
            _("Here is what happened on what you follow since our last message."),
            *lines,
        ],
        footer=settings_footer(),
    )


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
            Notification.objects(user=user, mail_pending=True).mark_mailed()
            continue

        # What was answered or read in the meantime is no news any more.
        Notification.objects(user=user, mail_pending=True, handled_at__ne=None).mark_mailed()
        due_before = datetime.now(UTC) - DIGEST_INTERVALS[user.mail_cadence]
        queue = Notification.objects(user=user, mail_pending=True)
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
                digest = notification_digest(notifications)
                if digest is not None:
                    digest.send(user)
                    sent += 1
            except Exception:
                log.exception(f"Could not send the notification digest of {user}")
                continue

        # Only what was mailed is spent: a notification arriving meanwhile stays queued.
        Notification.objects(
            id__in=[notification.id for notification in notifications]
        ).mark_mailed()

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
