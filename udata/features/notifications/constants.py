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
