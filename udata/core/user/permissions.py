# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from udata.auth import Permission, RoleNeed
from udata.i18n import lazy_gettext as _


ROLES = {
    'admin': _('System administrator'),
    'editor': _('Site editorialist'),
    'moderator': _('Site moderator'),
}

sysadmin = Permission(RoleNeed('admin'))
