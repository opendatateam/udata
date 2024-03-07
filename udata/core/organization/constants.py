from udata.i18n import lazy_gettext as _

__all__ = (
    'ORG_ROLES', 'DEFAULT_ROLE', 'MEMBERSHIP_STATUS', 'PUBLIC_SERVICE', 'CERTIFIED', 'LOGO_MAX_SIZE', 'LOGO_SIZES'
    'ASSOCIATION', 'COMPANY', 'LOCAL_AUTHORITY', 'TITLE_SIZE_LIMIT', 'DESCRIPTION_SIZE_LIMIT', 'ORG_BID_SIZE_LIMIT'
)

ORG_ROLES = {
    'admin': _('Administrator'),
    'editor': _('Editor'),
}
DEFAULT_ROLE = 'editor'


MEMBERSHIP_STATUS = {
    'pending': _('Pending'),
    'accepted': _('Accepted'),
    'refused': _('Refused'),
}

LOGO_MAX_SIZE = 500
LOGO_SIZES = [100, 60, 25]

PUBLIC_SERVICE = 'public-service'
CERTIFIED = 'certified'
ASSOCIATION = 'Association'
COMPANY = 'Company'
LOCAL_AUTHORITY = 'Local authority'

TITLE_SIZE_LIMIT = 350
DESCRIPTION_SIZE_LIMIT = 100000

ORG_BID_SIZE_LIMIT = 14