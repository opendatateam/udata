from flask_principal import Permission as BasePermission
from flask_principal import RoleNeed

from udata.auth import UserNeed
from udata.core.dataset.permissions import OwnablePermission
from udata.core.organization.permissions import (
    OrganizationAdminNeed,
    OrganizationEditorNeed,
    OrganizationPartialEditorNeed,
)


class PageEditPermission(OwnablePermission):
    pass


class PageReadPermission(BasePermission):
    """Everyone can read a published page, only its owners and sysadmins a draft.

    Inherits from BasePermission: an empty needs set allows everyone, whereas
    udata's Permission would always add the admin role to it.
    """

    def __init__(self, page):
        if page.is_visible:
            super().__init__()
            return

        needs = [RoleNeed("admin")]
        if page.organization:
            needs.append(OrganizationAdminNeed(page.organization.id))
            needs.append(OrganizationEditorNeed(page.organization.id))
            needs.append(OrganizationPartialEditorNeed(page.organization.id))
        elif page.owner:
            needs.append(UserNeed(page.owner.fs_uniquifier))

        super().__init__(*needs)
