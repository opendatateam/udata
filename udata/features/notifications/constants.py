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

# Notifications that answer a request the recipient made themselves, and reach nobody
# else. Turning them off would mean never learning whether one's own request went
# through, so they are not offered as a setting either.
PERSONAL_TYPES = frozenset(
    {
        NotificationType.ORGANIZATION_MEMBERSHIP_ACCEPTED,
        NotificationType.ORGANIZATION_MEMBERSHIP_REFUSED,
        NotificationType.HARVEST_SOURCE_ACCEPTED,
        NotificationType.HARVEST_SOURCE_REFUSED,
    }
)


# Notifications a whole organization hears at once, about the organization itself.
# They are broadcast like the configurable ones, but a badge is awarded once in the
# life of an organization: offering to mute it would add a switch nobody would ever
# look for.
ANNOUNCEMENT_TYPES = frozenset(
    {
        NotificationType.ORGANIZATION_BADGE_CERTIFIED,
        NotificationType.ORGANIZATION_BADGE_PUBLIC_SERVICE,
        NotificationType.ORGANIZATION_BADGE_COMPANY,
        NotificationType.ORGANIZATION_BADGE_ASSOCIATION,
        NotificationType.ORGANIZATION_BADGE_LOCAL_AUTHORITY,
    }
)


class NotificationCategory(StrEnum):
    """What a user chooses to hear about, in their own words.

    Deliberately coarser than `NotificationType`: the settings screen offers a handful
    of families, not the eighteen events feeding them.
    """

    DISCUSSIONS = "discussions"
    REUSES = "reuses"


# The family each type belongs to. A type absent from this mapping is not configurable,
# which is how the action-bound and personal ones stay out of the settings screen
# without a flag of their own.
CATEGORY_BY_TYPE: dict[NotificationType, NotificationCategory] = {
    NotificationType.DISCUSSION_NEW: NotificationCategory.DISCUSSIONS,
    NotificationType.DISCUSSION_COMMENT: NotificationCategory.DISCUSSIONS,
    NotificationType.DISCUSSION_CLOSED: NotificationCategory.DISCUSSIONS,
    NotificationType.REUSE_CREATED: NotificationCategory.REUSES,
    NotificationType.DATASERVICE_CREATED: NotificationCategory.REUSES,
}


class NotificationChannel(StrEnum):
    APP = "app"
    MAIL = "mail"


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


# `Organization.members` holds bare role strings, so the mapping is spelled out here.
REASON_BY_ORGANIZATION_ROLE: dict[str, NotificationReason] = {
    "admin": NotificationReason.ORGANIZATION_ADMIN,
    "editor": NotificationReason.ORGANIZATION_EDITOR,
    "partial_editor": NotificationReason.ORGANIZATION_PARTIAL_EDITOR,
}

# What somebody gets before they ever open the settings screen. Identical on every
# channel on purpose: a role has to stay readable as a single line. Individuals then
# deviate channel by channel, roles do not.
#
# Editors start silent: they are members of organizations whose datasets they have
# never touched, and mailing them every discussion of a 400-dataset organization is
# what this whole thing is meant to stop.
#
# Partial editors start loud, which only looks inconsistent: they are never given this
# reason unless the object was actually assigned to them, so "everything concerning
# me" is already a short list.
DEFAULT_ENABLED: dict[NotificationReason, bool] = {
    NotificationReason.OWNER: True,
    NotificationReason.ORGANIZATION_ADMIN: True,
    NotificationReason.ORGANIZATION_EDITOR: False,
    NotificationReason.ORGANIZATION_PARTIAL_EDITOR: True,
    NotificationReason.DISCUSSION_PARTICIPANT: True,
    NotificationReason.SYSADMIN: True,
    # Silent by default, which is not a contradiction: this reason only exists because
    # a decision said `True` somewhere, and that decision names a channel. Subscribing
    # to the bell must not sign one up for the mails too.
    NotificationReason.EXPLICIT_SUBSCRIBER: False,
}
