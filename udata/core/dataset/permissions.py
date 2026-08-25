from flask_principal import Permission as BasePermission
from flask_principal import RoleNeed

from udata.auth import Permission, UserNeed, admin_permission
from udata.core.organization.permissions import (
    AssignmentNeed,
    OrganizationAdminNeed,
    OrganizationEditorNeed,
    OrganizationPartialEditorNeed,
)

from .constants import is_reserved_extra
from .models import Resource


def can_write_extra(key: str) -> bool:
    """Whether the current user may write this extra key.

    Reserved extras (analysis, check, recommendations, transport, dcat...) are
    produced by platform services and trusted as-is by the frontend; letting users
    write them enables stored XSS and forged "platform-generated" metadata. Only a
    sysadmin may set them — Hydra and the other services authenticate as such.
    """
    return not is_reserved_extra(key) or admin_permission.can()


def sanitize_reserved_extras(before: dict, after: dict) -> dict:
    """Force reserved extras back to their stored values for non-sysadmins.

    The form write paths replace the whole extras dict, so a payload that does not
    echo a stored reserved key would erase it. Unlike the apiv2 extras endpoints,
    where every key is an explicit write intent and a reserved one is rejected, a
    full-object update legitimately echoes the extras it just read: reserved keys
    are silently restored here rather than turned into a validation error, like the
    hosted-resource fields in `BaseResourceForm`.
    """
    if admin_permission.can():
        return after
    sanitized = {key: value for key, value in after.items() if not is_reserved_extra(key)}
    sanitized.update({key: value for key, value in before.items() if is_reserved_extra(key)})
    return sanitized


class OwnablePermission(Permission):
    """A generic permission for ownable objects (with owner or organization)"""

    def __init__(self, obj):
        needs = []

        if obj.organization:
            needs.append(OrganizationAdminNeed(obj.organization.id))
            needs.append(OrganizationEditorNeed(obj.organization.id))
            needs.append(AssignmentNeed(obj.__class__.__name__, obj.id))
        elif obj.owner:
            needs.append(UserNeed(obj.owner.fs_uniquifier))

        super(OwnablePermission, self).__init__(*needs)


class OwnableReadPermission(BasePermission):
    """Permission to read a hidden ownable object (private or deleted).

    Always grants access if the object is visible (not private and not deleted).
    For hidden objects, requires owner, org member (any role), or sysadmin.

    We inherit from BasePermission instead of udata's Permission because
    Permission automatically adds RoleNeed("admin") to all needs. This means
    a permission with no needs would only allow admins. With BasePermission,
    an empty needs set allows everyone (Flask-Principal returns True when
    self.needs is empty).
    """

    def __init__(self, obj):
        is_private = getattr(obj, "private", False)
        is_deleted = bool(getattr(obj, "deleted", None) or getattr(obj, "deleted_at", None))
        if not is_private and not is_deleted:
            super().__init__()
            return

        needs = [RoleNeed("admin")]
        if obj.organization:
            needs.append(OrganizationAdminNeed(obj.organization.id))
            needs.append(OrganizationEditorNeed(obj.organization.id))
            needs.append(OrganizationPartialEditorNeed(obj.organization.id))
        elif obj.owner:
            needs.append(UserNeed(obj.owner.fs_uniquifier))

        super().__init__(*needs)


class DatasetEditPermission(OwnablePermission):
    """Permissions to edit a Dataset"""

    pass


class ResourceEditPermission(OwnablePermission):
    """Permissions to edit a Resource (aka. its dataset) or community resource"""

    def __init__(self, obj):
        if isinstance(obj, Resource):
            raise ValueError("Resource permissions are holded by its dataset")
        super(ResourceEditPermission, self).__init__(obj)
