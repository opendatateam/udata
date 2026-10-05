from collections import Counter
from typing import TYPE_CHECKING

from udata.features.notifications.constants import NotificationType
from udata.i18n import lazy_gettext as _
from udata.mail import LabelledContent, MailCTA, MailMessage
from udata.uris import cdata_url

if TYPE_CHECKING:
    from udata.core.discussions.models import Discussion
    from udata.features.notifications.models import Notification

# The types a digest can summarize, and how each reads once counted. Being listed here
# is what lets a notification wait for the digest instead of being mailed at once.
#
# Both forms are spelled out: gettext plurals are per-language, and
# "1 nouvelle discussion" / "3 nouvelles discussions" cannot be derived from one string.
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
}


def _counted(type: NotificationType, count: int) -> str:
    singular, plural = DIGEST_COUNTS[type]
    return str(singular if count == 1 else plural) % {"count": count}


def notification_digest(notifications: list["Notification"]) -> MailMessage | None:
    """What happened since the last digest, or `None` when nothing is left to say.

    One line per discussion rather than one per notification, because a busy thread
    would otherwise fill the mail with the same title repeated.
    """
    # Insertion order keeps the oldest subject first, which is the order the queue was
    # read in.
    counts: dict["Discussion", Counter[NotificationType]] = {}
    for notification in notifications:
        subject = notification.details.discussion
        if subject is None:
            # The subject went away between the event and the digest; the notification
            # is on its way out too.
            continue
        counts.setdefault(subject, Counter())[notification.type] += 1

    if not counts:
        return None

    lines = [
        LabelledContent(
            subject.title,
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
