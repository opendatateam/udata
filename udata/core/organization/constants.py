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

TITLE_SIZE_LIMIT = 350
DESCRIPTION_SIZE_LIMIT = 100000

ORG_BID_SIZE_LIMIT = 14
