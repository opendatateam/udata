from flask_principal import Permission as BasePermission
from flask_principal import RoleNeed

from udata.auth import Permission, UserNeed
from udata.core.organization.permissions import (
    OrganizationAdminNeed,
    OrganizationEditorNeed,
)

from .models import Resource


class OwnablePermission(Permission):
    """A generic permission for ownable objects (with owner or organization)"""

    def __init__(self, obj):
        needs = []

        if obj.organization:
            needs.append(OrganizationAdminNeed(obj.organization.id))
            needs.append(OrganizationEditorNeed(obj.organization.id))
        elif obj.owner:
            needs.append(UserNeed(obj.owner.fs_uniquifier))

        super(OwnablePermission, self).__init__(*needs)


class OwnableReadPermission(BasePermission):
    """Permission to read a private ownable object.

    Always grants access if the object is not private.
    For private objects, requires owner, org member, or sysadmin.

    We inherit from BasePermission instead of udata's Permission because
    Permission automatically adds RoleNeed("admin") to all needs. This means
    a permission with no needs would only allow admins. With BasePermission,
    an empty needs set allows everyone (Flask-Principal returns True when
    self.needs is empty).
    """

    def __init__(self, obj):
        if not getattr(obj, "private", False):
            super().__init__()
            return

        needs = [RoleNeed("admin")]
        if obj.organization:
            needs.append(OrganizationAdminNeed(obj.organization.id))
            needs.append(OrganizationEditorNeed(obj.organization.id))
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
