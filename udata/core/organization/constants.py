from typing import NamedTuple

from udata.i18n import lazy_gettext as _


class OrgRole(NamedTuple):
    label: str
    description: str


ORG_ROLES = {
    "admin": OrgRole(
        _("Administrator"),
        _("Can manage the organization, its members and all its content."),
    ),
    "editor": OrgRole(
        _("Editor"),
        _("Can create and edit all the content of the organization."),
    ),
    "partial_editor": OrgRole(
        _("Partial editor"),
        _("Can create content and edit only some of the content."),
    ),
}
DEFAULT_ROLE = "editor"


MEMBERSHIP_STATUS = {
    "pending": _("Pending"),
    "accepted": _("Accepted"),
    "refused": _("Refused"),
    "canceled": _("Canceled"),
}

REQUEST_TYPES = {
    "request": _("Request"),
    "invitation": _("Invitation"),
}

LOGO_MAX_SIZE = 500
LOGO_SIZES = [100, 60, 25]
BIGGEST_LOGO_SIZE = LOGO_SIZES[0]

# Organization page banner (data.gouv.fr#2049)
BANNER_MAX_BYTES = 4 * 1024 * 1024  # Upload cap from the issue: 4 Mo
BANNER_MAX_DIMENSION = 1920  # Served image is capped at this many pixels (longest side)
BANNER_MIN_SIZE = (1200, 300)  # Full-width `cover` display (#2049): floor against heavy upscaling

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


ASSIGNABLE_OBJECT_TYPES = {"Dataset", "Dataservice", "Reuse"}

TITLE_SIZE_LIMIT = 350
DESCRIPTION_SIZE_LIMIT = 100000

ORG_BID_SIZE_LIMIT = 14
