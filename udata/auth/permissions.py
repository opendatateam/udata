from __future__ import annotations

from abc import ABC, abstractmethod

from flask_security import current_user


class PermissionDenied(Exception):
    pass


class Permission(ABC):
    @abstractmethod
    def check(self) -> bool: ...

    def can(self) -> bool:
        if current_user.is_authenticated and current_user.sysadmin:
            return True
        return self.check()

    def test(self):
        if not self.can():
            raise PermissionDenied("You do not have the permission to modify that object.")

    def require(self):
        """Compatibility with @api.secure which does `with permission.require():`"""
        return _PermissionContext(self)

    def __bool__(self) -> bool:
        return self.can()

    def __or__(self, other: Permission) -> Permission:
        lefts = self._permissions if isinstance(self, AnyOf) else (self,)
        rights = other._permissions if isinstance(other, AnyOf) else (other,)
        return AnyOf(*lefts, *rights)

    def __and__(self, other: Permission) -> Permission:
        lefts = self._permissions if isinstance(self, AllOf) else (self,)
        rights = other._permissions if isinstance(other, AllOf) else (other,)
        return AllOf(*lefts, *rights)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class _PermissionContext:
    def __init__(self, permission: Permission):
        self._permission = permission

    def __enter__(self):
        if not self._permission.can():
            raise PermissionDenied("You do not have the permission to modify that object.")
        return self

    def __exit__(self, *args):
        pass

    def can(self):
        return self._permission.can()


# --- Leaf predicates ---


class Allow(Permission):
    def check(self) -> bool:
        return True


class Deny(Permission):
    def check(self) -> bool:
        return False


class Authenticated(Permission):
    def check(self) -> bool:
        return current_user.is_authenticated


class IsUser(Permission):
    def __init__(self, user):
        self._user_id = user.id if hasattr(user, "id") else user

    def check(self) -> bool:
        return current_user.is_authenticated and current_user.id == self._user_id

    def __repr__(self) -> str:
        return f"<IsUser {self._user_id}>"


class HasRole(Permission):
    def __init__(self, role: str):
        self._role = role

    def check(self) -> bool:
        return current_user.is_authenticated and current_user.has_role(self._role)

    def __repr__(self) -> str:
        return f"<HasRole {self._role}>"


class HasOrgRole(Permission):
    def __init__(self, organization, *roles: str):
        self._organization = organization
        self._roles = set(roles)

    def check(self) -> bool:
        if not current_user.is_authenticated or not self._organization:
            return False
        member = self._organization.member(current_user._get_current_object())
        return member is not None and member.role in self._roles

    def __repr__(self) -> str:
        return f"<HasOrgRole {self._roles}>"


class HasObjectPermission(Permission):
    """For partial editors: checks if the user has an explicit
    per-object permission stored in the database.
    """

    def __init__(self, obj):
        self._obj = obj

    def check(self) -> bool:
        if not current_user.is_authenticated:
            return False
        from udata.core.object_permissions.models import ObjectPermission

        return ObjectPermission.objects(
            user=current_user.id,
            subject_class=type(self._obj).__name__,
            subject_id=self._obj.id,
        ).first() is not None

    def __repr__(self) -> str:
        return f"<HasObjectPermission {type(self._obj).__name__}:{self._obj.id}>"


# --- Combinators ---


class AnyOf(Permission):
    def __init__(self, *permissions: Permission):
        self._permissions = permissions

    def check(self) -> bool:
        return any(p.check() for p in self._permissions)

    def __repr__(self) -> str:
        return f"<AnyOf {' | '.join(repr(p) for p in self._permissions)}>"


class AllOf(Permission):
    def __init__(self, *permissions: Permission):
        self._permissions = permissions

    def check(self) -> bool:
        return all(p.check() for p in self._permissions)

    def __repr__(self) -> str:
        return f"<AllOf {' & '.join(repr(p) for p in self._permissions)}>"


# --- Convenience ---

admin_permission = HasRole("admin")
