from collections import Counter
from collections.abc import Callable
from typing import TYPE_CHECKING

from udata.features.notifications.constants import NotificationType
from udata.i18n import lazy_gettext as _
from udata.i18n import lazy_ngettext, ngettext
from udata.mail import LabelledContent, MailCTA, MailMessage
from udata.uris import cdata_url

if TYPE_CHECKING:
    from udata.core.discussions.models import Discussion
    from udata.features.notifications.models import Notification

# The types a digest can summarize, and how each reads once counted. Being listed here
# is what lets a notification wait for the digest instead of being mailed at once.
DIGEST_COUNTS: dict[NotificationType, Callable[[int], str]] = {
    NotificationType.DISCUSSION_NEW: lambda count: ngettext(
        "%(num)d new discussion", "%(num)d new discussions", count
    ),
    NotificationType.DISCUSSION_COMMENT: lambda count: ngettext(
        "%(num)d new comment", "%(num)d new comments", count
    ),
    NotificationType.DISCUSSION_CLOSED: lambda count: ngettext(
        "%(num)d closed discussion", "%(num)d closed discussions", count
    ),
}


def notification_digest(notifications: list["Notification"]) -> MailMessage:
    """What happened since the last digest.

    One line per discussion rather than one per notification, because a busy thread
    would otherwise fill the mail with the same title repeated.
    """
    # Insertion order keeps the oldest subject first, which is the order the queue was
    # read in.
    counts: dict["Discussion", Counter[NotificationType]] = {}
    for notification in notifications:
        counts.setdefault(notification.details.discussion, Counter())[notification.type] += 1

    lines = [
        LabelledContent(
            subject.title,
            ", ".join(DIGEST_COUNTS[type](count) for type, count in by_type.items()),
            inline=True,
        )
        for subject, by_type in counts.items()
    ]

    return MailMessage(
        subject=lazy_ngettext(
            "%(num)d update on what you follow", "%(num)d updates on what you follow", len(lines)
        ),
        paragraphs=[
            _("Here is what happened on what you follow since our last message."),
            *lines,
            MailCTA(_("See all my notifications"), cdata_url("/admin/me/notifications")),
        ],
        footer=settings_footer(),
    )


def settings_footer() -> MailCTA:
    """The way out of every mail about something one never asked for by name."""
    return MailCTA(
        _("Manage or turn off these notifications"), cdata_url("/admin/me/notifications")
    )
