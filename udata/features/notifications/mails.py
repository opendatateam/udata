from flask_babel import LazyString

from udata.core.organization.models import Organization
from udata.features.notifications.constants import NotificationReason
from udata.i18n import lazy_gettext as _
from udata.mail import MailCTA
from udata.uris import cdata_url


def reason_sentence(reason: NotificationReason, subject, followed=None) -> LazyString:
    """Why one receives a mail about `subject`, in the words of the reason. A follow names
    what is followed (`followed`): the thread, the subject or its organization."""
    organization = (
        subject if isinstance(subject, Organization) else getattr(subject, "organization", None)
    )
    followed_name = str(followed or subject)
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
