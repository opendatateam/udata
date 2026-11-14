from flask_principal import Permission as BasePermission
from flask_principal import RoleNeed

from udata.auth import UserNeed
from udata.core.organization.permissions import (
    OrganizationAdminNeed,
    OrganizationEditorNeed,
    OrganizationPartialEditorNeed,
)


class PostReadPermission(BasePermission):
    """Permission to read a post: everyone for a published one, its owners and sysadmins for a draft.

    We inherit from BasePermission instead of udata's Permission because
    Permission automatically adds RoleNeed("admin") to all needs. This means
    a permission with no needs would only allow admins. With BasePermission,
    an empty needs set allows everyone (Flask-Principal returns True when
    self.needs is empty).
    """

    def __init__(self, post):
        if post.is_visible:
            super().__init__()
            return

        needs = [RoleNeed("admin")]
        if post.is_external_page:
            if post.organization:
                needs.append(OrganizationAdminNeed(post.organization.id))
                needs.append(OrganizationEditorNeed(post.organization.id))
                needs.append(OrganizationPartialEditorNeed(post.organization.id))
            elif post.owner:
                needs.append(UserNeed(post.owner.fs_uniquifier))

        super().__init__(*needs)
