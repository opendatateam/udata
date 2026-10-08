from collections import Counter
from typing import TYPE_CHECKING

from flask_babel import LazyString
from mongoengine import DoesNotExist

from udata.core.discussions.models import Discussion
from udata.core.organization.models import Organization
from udata.features.notifications.constants import NotificationReason, NotificationType
from udata.i18n import lazy_gettext as _
from udata.i18n import lazy_ngettext
from udata.mail import Link, MailCTA, MailMessage, ParagraphWithLinks
from udata.uris import cdata_url

if TYPE_CHECKING:
    from udata.features.notifications.models import Notification


def notification_digest(notifications: list["Notification"]) -> MailMessage | None:
    """What happened since the last digest, `None` when nothing of it is left to tell.

    One line per subject rather than one per notification, because a busy thread would
    otherwise fill the mail with the same title repeated. Each event says what its line
    is about and how it counts (`digest_subject`, `digest_count`).

    A notification whose subject is gone (a post deleted with its discussions left
    behind) is left out: failing on it would hold back the whole digest, run after run.
    """
    # `events` builds on this module, hence the import at call time.
    from udata.features.notifications.events import event_for_type

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


def reason_sentence(reason: NotificationReason, subject, followed=None) -> LazyString:
    """Why one receives a mail about `subject`, in the words of the reason. A follow names
    what is followed (`followed`): the thread, the subject or its organization."""
    organization = (
        subject if isinstance(subject, Organization) else getattr(subject, "organization", None)
    )
    followed = followed or subject
    followed_name = followed.title if isinstance(followed, Discussion) else str(followed)
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
        case NotificationReason.ORGANIZATION_PARTIAL_EDITOR if subject is organization:
            # Something about the organization as a whole (a badge) reaches all of its
            # members: nothing of it was assigned to them.
            return _(
                "You receive this email because you are a partial editor of %(organization)s.",
                organization=organization.name,
            )
        case NotificationReason.ORGANIZATION_PARTIAL_EDITOR:
            return _(
                "You receive this email because %(subject)s is assigned to you.",
                subject=str(subject),
            )
        case NotificationReason.DISCUSSION_PARTICIPANT:
            return _("You receive this email because you take part in this discussion.")
        case NotificationReason.EXPLICIT_SUBSCRIBER:
            return _(
                "You receive this email because you follow %(subject)s.", subject=followed_name
            )
        case NotificationReason.CONTRIBUTOR:
            return _(
                "You receive this email because you edited %(subject)s.", subject=followed_name
            )
        case NotificationReason.DISCUSSANT:
            return _(
                "You receive this email because you took part in the discussions of %(subject)s.",
                subject=followed_name,
            )
        case NotificationReason.REQUESTER:
            return _("You receive this email because you made this request.")
        case NotificationReason.SYSADMIN:
            return _("You receive this email because you administer the site.")


def way_out(label: LazyString, scope=None, event: str | None = None) -> MailCTA:
    """A link to the settings page, which offers to stop what the link names and only
    does so once confirmed: a mail scanner opening the link must not unsubscribe anyone.
    The keys are those of the rule to write, as `/notifications/resolved/` takes them."""
    keys = {}
    if scope is not None:
        keys["scope"] = f"{scope.__class__.__name__}:{scope.id}"
    if event is not None:
        keys["event"] = event
    return MailCTA(label, cdata_url("/admin/me/notifications", **keys))


def settings_footer(
    reasons=(), subject=None, ways_out: list[MailCTA] = (), followed=None
) -> list[LazyString | MailCTA]:
    """Why one receives a mail, every reason of it, and the ways out, the same as the
    bell offers. Naming only one reason would offer a way out that stops nothing: the
    most generous one wins."""
    return [
        *(reason_sentence(reason, subject, followed) for reason in sorted(reasons)),
        *ways_out,
        MailCTA(_("Manage your notifications"), cdata_url("/admin/me/notifications")),
    ]
