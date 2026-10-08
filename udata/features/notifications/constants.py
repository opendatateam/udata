from enum import StrEnum


class NotificationType(StrEnum):
    """Identifies what happened, independently of the payload shape it carries.

    Several types share a single `details` class when they describe the same
    subject (the three discussion types, the five badge types…): the type says
    what happened, the `details` class says which fields are available.
    """

    DISCUSSION_NEW = "discussion.new"
    DISCUSSION_COMMENT = "discussion.comment"
    DISCUSSION_CLOSED = "discussion.closed"

    ORGANIZATION_MEMBERSHIP_REQUESTED = "organization.membership.requested"
    ORGANIZATION_MEMBERSHIP_INVITED = "organization.membership.invited"
    ORGANIZATION_MEMBERSHIP_ACCEPTED = "organization.membership.accepted"
    ORGANIZATION_MEMBERSHIP_REFUSED = "organization.membership.refused"

    ORGANIZATION_BADGE_CERTIFIED = "organization.badge.certified"
    ORGANIZATION_BADGE_PUBLIC_SERVICE = "organization.badge.public-service"
    ORGANIZATION_BADGE_COMPANY = "organization.badge.company"
    ORGANIZATION_BADGE_ASSOCIATION = "organization.badge.association"
    ORGANIZATION_BADGE_LOCAL_AUTHORITY = "organization.badge.local-authority"

    REUSE_CREATED = "reuse.created"

    DATASERVICE_CREATED = "dataservice.created"

    TRANSFER_REQUESTED = "transfer.requested"

    HARVEST_SOURCE_PENDING = "harvest.source.pending"
    HARVEST_SOURCE_ACCEPTED = "harvest.source.accepted"
    HARVEST_SOURCE_REFUSED = "harvest.source.refused"


# The family of the five badge types: a rule naming it covers them all.
ORGANIZATION_BADGES = "organization.badge"


def event_chain(event: str | None) -> list[str]:
    """What a rule about this event can name, from the narrowest to the broadest: the
    type itself, then each of its dotted prefixes. `discussion.comment` yields
    `["discussion.comment", "discussion"]`; a rule naming no event covers them all.

    Grouping by prefix rather than by class keeps what a rule means apart from how the
    events share their code: refactoring a base class must not change who hears what.
    """
    if not event:
        return []
    parts = event.split(".")
    return [".".join(parts[:length]) for length in range(len(parts), 0, -1)]


def is_event_name(event: str) -> bool:
    """Whether a rule can name `event`: a notification type, or a prefix of some."""
    return any(type == event or type.startswith(f"{event}.") for type in NotificationType)


# Notifications that are resolved by acting on their subject (accepting a request,
# validating a source) rather than by reading them. Exposed as `requires_action` so the
# front doesn't offer to mark them as read; the API accepts it on any notification.
TYPES_REQUIRING_ACTION = frozenset(
    {
        NotificationType.ORGANIZATION_MEMBERSHIP_REQUESTED,
        NotificationType.ORGANIZATION_MEMBERSHIP_INVITED,
        NotificationType.TRANSFER_REQUESTED,
        NotificationType.HARVEST_SOURCE_PENDING,
    }
)


class MailCadence(StrEnum):
    """How often somebody agrees to be written to.

    A property of the person, not of the subject: letting one organization be weekly
    and another daily would turn every digest into a join over cadences before a single
    mail could be composed, for a need nobody expressed. What is scoped is *whether*
    something concerns you; this is only the rhythm it reaches you at.
    """

    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"


class NotificationReason(StrEnum):
    """Why this recipient is concerned by this event.

    Carries the organization role rather than a bare "member" for two reasons: the
    default a recipient falls back on depends on it, and the mail footer says
    "because you administer X" instead of something the reader has to guess.
    """

    OWNER = "owner"
    ORGANIZATION_ADMIN = "organization.admin"
    ORGANIZATION_EDITOR = "organization.editor"
    ORGANIZATION_PARTIAL_EDITOR = "organization.partial_editor"
    DISCUSSION_PARTICIPANT = "discussion.participant"
    SYSADMIN = "sysadmin"
    # Asked for it on this very subject, without being concerned otherwise. The only
    # way somebody outside an organization can follow a thread or a dataset.
    EXPLICIT_SUBSCRIBER = "explicit_subscriber"
    # Edited this very subject: followed without asking, for having worked on it.
    CONTRIBUTOR = "contributor"
    # Took part in the discussions of this very subject, as a member of its organization:
    # followed without asking, for having answered about it.
    DISCUSSANT = "discussant"
    # Made the request this notification answers (a membership, a harvest source).
    REQUESTER = "requester"


class FollowOrigin(StrEnum):
    """What made a user follow a subject, which decides the reason the follow gives."""

    FOLLOWED = "followed"
    EDITED = "edited"
    DISCUSSED = "discussed"


# `Organization.members` holds bare role strings, so the mapping is spelled out here.
REASON_BY_ORGANIZATION_ROLE: dict[str, NotificationReason] = {
    "admin": NotificationReason.ORGANIZATION_ADMIN,
    "editor": NotificationReason.ORGANIZATION_EDITOR,
    "partial_editor": NotificationReason.ORGANIZATION_PARTIAL_EDITOR,
}
