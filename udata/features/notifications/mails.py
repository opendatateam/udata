from collections import Counter
from typing import TYPE_CHECKING

from flask_babel import LazyString

from udata.features.notifications.constants import NotificationReason, NotificationType
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


def reason_sentence(reason: NotificationReason, subject) -> LazyString:
    """Why one receives a mail about `subject`, in the words of the reason."""
    organization = getattr(subject, "organization", None)
    match reason:
        case NotificationReason.OWNER:
            return _("You receive this email because you own %(subject)s.", subject=str(subject))
        case NotificationReason.ORGANIZATION_ADMIN:
            return _(
                "You receive this email because you administer %(organization)s.",
                organization=organization.name,
            )
        case NotificationReason.ORGANIZATION_EDITOR:
            return _(
                "You receive this email because you are an editor of %(organization)s.",
                organization=organization.name,
            )
        case NotificationReason.ORGANIZATION_PARTIAL_EDITOR:
            return _(
                "You receive this email because %(subject)s was assigned to you.",
                subject=str(subject),
            )
        case NotificationReason.DISCUSSION_PARTICIPANT:
            return _("You receive this email because you take part in this discussion.")
        case NotificationReason.EXPLICIT_SUBSCRIBER:
            return _("You receive this email because you follow %(subject)s.", subject=str(subject))
        case NotificationReason.SYSADMIN:
            return _("You receive this email because you administer the site.")


def settings_footer(reasons=(), subject=None) -> list[LazyString | MailCTA]:
    """Why one receives a mail, every reason of it, and the way out. Naming only one
    reason would offer a way out that stops nothing: the most generous one wins."""
    return [
        *(reason_sentence(reason, subject) for reason in sorted(reasons)),
        MailCTA(_("Manage or turn off these notifications"), cdata_url("/admin/me/notifications")),
    ]
