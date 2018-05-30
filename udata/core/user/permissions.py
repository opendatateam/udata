from udata.auth import Permission, RoleNeed, UserNeed
from udata.i18n import lazy_gettext as _


ROLES = {
    'admin': _('System administrator'),
    'editor': _('Site editorialist'),
    'moderator': _('Site moderator'),
}

sysadmin = Permission(RoleNeed('admin'))


class UserEditPermission(Permission):
    def __init__(self, user):
        need = UserNeed(user.id)
        super(UserEditPermission, self).__init__(need)
