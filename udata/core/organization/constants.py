from udata.i18n import lazy_gettext as _

ORG_ROLES = {
    "admin": _("Administrator"),
    "editor": _("Editor"),
}
DEFAULT_ROLE = "editor"


MEMBERSHIP_STATUS = {
    "pending": _("Pending"),
    "accepted": _("Accepted"),
    "refused": _("Refused"),
}

LOGO_MAX_SIZE = 500
LOGO_SIZES = [100, 60, 25]
BIGGEST_LOGO_SIZE = LOGO_SIZES[0]

PUBLIC_SERVICE = "public-service"
CERTIFIED = "certified"
ASSOCIATION = "association"
COMPANY = "company"
LOCAL_AUTHORITY = "local-authority"

# Special value for content published by individual users (not organizations)
USER = "user"

# Special value for content published by organizations without producer badges
NOT_SPECIFIED = "not-specified"

# Badge types that are producer types (used for filtering in get_producer_type)
PRODUCER_BADGE_TYPES = frozenset({PUBLIC_SERVICE, ASSOCIATION, COMPANY, LOCAL_AUTHORITY})

# All producer types for filtering (includes USER and NOT_SPECIFIED)
PRODUCER_TYPES = frozenset({PUBLIC_SERVICE, ASSOCIATION, COMPANY, LOCAL_AUTHORITY, USER, NOT_SPECIFIED})


def get_producer_type(organization, owner) -> list[str]:
    """
    Determine the producer type(s) for a dataset/dataservice/reuse.

    Returns a list of producer types based on organization badges,
    ['not-specified'] if published by an organization without producer badges,
    or ['user'] if published by an individual user.

    Args:
        organization: The organization object (or None)
        owner: The owner user object (or None)

    Returns:
        A list of producer type strings
    """
    if organization is not None:
        # Return badges that are producer types (exclude CERTIFIED)
        if hasattr(organization, 'badges') and organization.badges:
            producer_badges = [badge.kind for badge in organization.badges if badge.kind in PRODUCER_BADGE_TYPES]
            if producer_badges:
                return producer_badges
        # Organization exists but has no producer badges
        return [NOT_SPECIFIED]
    elif owner is not None:
        return [USER]
    return []


TITLE_SIZE_LIMIT = 350
DESCRIPTION_SIZE_LIMIT = 100000

ORG_BID_SIZE_LIMIT = 14
