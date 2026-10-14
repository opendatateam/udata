from flask_principal import Permission as BasePermission
from flask_principal import RoleNeed

from udata.auth import Permission


class PostEditPermission(Permission):
    pass


class PostReadPermission(BasePermission):
    """Permission to read a post: everyone for a published one, sysadmins only for a draft.

    We inherit from BasePermission instead of udata's Permission because
    Permission automatically adds RoleNeed("admin") to all needs. This means
    a permission with no needs would only allow admins. With BasePermission,
    an empty needs set allows everyone (Flask-Principal returns True when
    self.needs is empty).
    """

    def __init__(self, post):
        needs = [] if post.is_visible else [RoleNeed("admin")]
        super().__init__(*needs)
