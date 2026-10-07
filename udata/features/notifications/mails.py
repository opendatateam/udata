from collections import Counter
from typing import TYPE_CHECKING

from udata.features.notifications.constants import NotificationType
from udata.i18n import lazy_gettext as _
from udata.i18n import lazy_ngettext
from udata.mail import LabelledContent, MailCTA, MailMessage
from udata.uris import cdata_url

if TYPE_CHECKING:
    from udata.features.notifications.models import Notification


def notification_digest(notifications: list["Notification"]) -> MailMessage:
    """What happened since the last digest.

    One line per subject rather than one per notification, because a busy thread would
    otherwise fill the mail with the same title repeated. Each event says what its line
    is about and how it counts (`digest_subject`, `digest_count`).
    """
    # `events` builds on this module, hence the import at call time.
    from udata.features.notifications.events import event_for_type

    # Insertion order keeps the oldest subject first, which is the order the queue was
    # read in.
    titles: dict[object, str] = {}
    counts: dict[object, Counter[NotificationType]] = {}
    for notification in notifications:
        key, title = event_for_type(notification.type).digest_subject(notification.details)
        titles.setdefault(key, title)
        counts.setdefault(key, Counter())[notification.type] += 1

    lines = [
        LabelledContent(
            titles[key],
            ", ".join(
                event_for_type(type).digest_count(count) for type, count in by_type.items()
            ),
            inline=True,
        )
        for key, by_type in counts.items()
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
