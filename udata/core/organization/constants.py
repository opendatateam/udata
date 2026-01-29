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
PRODUCER_TYPES = frozenset(
    {PUBLIC_SERVICE, ASSOCIATION, COMPANY, LOCAL_AUTHORITY, USER, NOT_SPECIFIED}
)


TITLE_SIZE_LIMIT = 350
DESCRIPTION_SIZE_LIMIT = 100000

ORG_BID_SIZE_LIMIT = 14
