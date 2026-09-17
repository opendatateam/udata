from collections import Counter

from udata.features.notifications.constants import NotificationType
from udata.i18n import lazy_gettext as _
from udata.mail import LabelledContent, MailCTA, MailMessage
from udata.uris import cdata_url


def _discussion_subject(notification):
    """The thread itself: three answers in a row are one thing that happened."""
    return notification.details.discussion


def _reused_dataset(notification):
    return notification.details.dataset


# What a digest line is about, per type. Notifications sharing a subject collapse into
# a single line, so three comments read as "3 new comments" rather than three entries
# saying the same thing.
DIGEST_SUBJECT = {
    NotificationType.DISCUSSION_NEW: _discussion_subject,
    NotificationType.DISCUSSION_COMMENT: _discussion_subject,
    NotificationType.DISCUSSION_CLOSED: _discussion_subject,
    NotificationType.REUSE_CREATED: _reused_dataset,
    NotificationType.DATASERVICE_CREATED: _reused_dataset,
}

# How each type reads once counted. Both forms are spelled out: gettext plurals are
# per-language, and "1 nouvelle discussion" / "3 nouvelles discussions" cannot be
# derived from one string.
DIGEST_COUNTS = {
    NotificationType.DISCUSSION_NEW: (
        _("%(count)d new discussion"),
        _("%(count)d new discussions"),
    ),
    NotificationType.DISCUSSION_COMMENT: (_("%(count)d new comment"), _("%(count)d new comments")),
    NotificationType.DISCUSSION_CLOSED: (
        _("%(count)d closed discussion"),
        _("%(count)d closed discussions"),
    ),
    NotificationType.REUSE_CREATED: (_("%(count)d new reuse"), _("%(count)d new reuses")),
    NotificationType.DATASERVICE_CREATED: (_("%(count)d new API"), _("%(count)d new APIs")),
}


def _counted(type: NotificationType, count: int) -> str:
    singular, plural = DIGEST_COUNTS[type]
    return str(singular if count == 1 else plural) % {"count": count}


def notification_digest(notifications: list) -> MailMessage | None:
    """What happened since the last digest, or `None` when nothing is left to say.

    One line per subject rather than one per notification, because a busy thread would
    otherwise fill the mail with the same title repeated.
    """
    # Insertion order keeps the oldest subject first, which is the order the queue was
    # read in.
    counts: dict = {}
    for notification in notifications:
        subject = DIGEST_SUBJECT[notification.type](notification)
        if subject is None:
            # The subject went away between the event and the digest; the notification
            # is on its way out too.
            continue
        counts.setdefault(subject, Counter())[notification.type] += 1

    if not counts:
        return None

    lines = [
        LabelledContent(
            str(subject),
            ", ".join(_counted(type, count) for type, count in by_type.items()),
            inline=True,
        )
        for subject, by_type in counts.items()
    ]

    return MailMessage(
        subject=_("%(count)d update(s) on what you follow", count=len(lines)),
        paragraphs=[
            _("Here is what happened on what you follow since our last message."),
            *lines,
            MailCTA(_("See all my notifications"), cdata_url("/admin/me/notifications")),
        ],
    )
