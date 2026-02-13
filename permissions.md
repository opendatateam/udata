# Système de permissions udata

### Principes

1. **Les permissions sont des prédicats composables.** Une permission = une question "le user courant peut-il faire X ?", évaluée paresseusement.
2. **Composition avec `|` et `&`.** Pas de listes de needs, pas d'intersection d'ensembles. Juste de la logique booléenne.
3. **Évaluation lazy.** Pas de pre-loading. L'appartenance à une org est vérifiée au moment du check, pas au chargement de l'identité.
4. **Admin bypass intégré dans `can()`.** Chaque permission accorde automatiquement l'accès aux sysadmins.
5. **Aucune dépendance à Flask-Principal.** Flask-Principal reste installé (Flask-Security-Too en a besoin) mais on n'utilise plus ses classes Permission/Need.
6. **Même interface publique.** `permission.can()`, `.test()`, `bool(permission)` fonctionnent comme avant. La sérialisation API (`fields.Permission` appelle `.can()`) ne change pas.
7. **`AccessPolicy` = source de vérité unique.** Un seul objet par modèle définit les règles d'accès. Il génère à la fois les permissions per-object (prédicats Python) et les filtres queryset (MongoDB Q / Elasticsearch DSL).

### Implémentation

#### `udata/auth/permissions.py` — Les primitives

```python
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
```

#### `udata/auth/policies.py` — `AccessPolicy`

Source de vérité unique : porte les règles d'accès et sait générer les permissions per-object ET les filtres queryset (MongoDB, et plus tard Elasticsearch).

```python
from mongoengine import Q

from udata.auth.permissions import (
    Allow,
    Deny,
    HasObjectPermission,
    HasOrgRole,
    IsUser,
    Permission,
)


class AccessPolicy:
    def __init__(self, org_roles, public_filter=None):
        self._org_roles = org_roles
        self._public_filter = public_filter or Q()

    # --- Per-object (API views, .test(), sérialisation frontend) ---

    def permission(self, obj) -> Permission:
        if obj.organization:
            return HasOrgRole(obj.organization, *self._org_roles) | HasObjectPermission(obj)
        if obj.owner:
            return IsUser(obj.owner)
        return Deny()

    def read_permission(self, obj) -> Permission:
        """Visibility check for a single object.

        Public objects → Allow (everyone, including anonymous).
        Private objects → same rules as permission().
        """
        if not getattr(obj, "private", False):
            return Allow()
        return self.permission(obj)

    # --- Queryset (listings, exports) ---

    def queryset(self, qs, user=None):
        """Filter a queryset. Replaces both visible() and visible_by_user().

        - No user / anonymous → public items only (applies public_filter)
        - Sysadmin → everything
        - Authenticated → public items + items the user can access
        """
        if user is None or user.is_anonymous:
            return qs(self._public_filter)
        if user.sysadmin:
            return qs

        q = Q(owner=user.id)

        org_ids = self._org_ids_for_user(user)
        if org_ids:
            q |= Q(organization__in=org_ids)

        assigned_ids = self._assigned_ids_for_user(user, qs._document)
        if assigned_ids:
            q |= Q(id__in=assigned_ids)

        return qs(self._public_filter | q)

    # --- Elasticsearch (search) ---

    def es_filter(self, user, document_class):
        """Elasticsearch filter. Same logic as queryset(), different output format."""
        if user is None or user.is_anonymous:
            return None  # ES adapter already applies public filters
        if user.sysadmin:
            return {"match_all": {}}

        should = [
            {"term": {"owner": str(user.id)}},
        ]

        org_ids = self._org_ids_for_user(user)
        if org_ids:
            should.append({"terms": {"organization": [str(id) for id in org_ids]}})

        assigned_ids = self._assigned_ids_for_user(user, document_class)
        if assigned_ids:
            should.append({"ids": {"values": [str(id) for id in assigned_ids]}})

        return {"bool": {"should": should, "minimum_should_match": 1}}

    # --- Shared logic ---

    def _org_ids_for_user(self, user):
        return [
            org.id
            for org in user.organizations
            if (m := org.member(user)) and m.role in self._org_roles
        ]

    def _assigned_ids_for_user(self, user, document_class):
        from udata.core.object_permissions.models import ObjectPermission

        return ObjectPermission.objects(
            user=user.id,
            subject_class=document_class.__name__,
        ).distinct("subject_id")
```

#### `udata/core/object_permissions/models.py` — Le modèle pour les permissions par objet

```python
from mongoengine import fields as db

from udata.mongo import UDataDocument


class ObjectPermission(UDataDocument):
    """Grants a specific user edit access to a specific object.

    Used for partial editors: org members who can only edit
    objects explicitly assigned to them.
    """

    user = db.ReferenceField("User", required=True)
    organization = db.ReferenceField("Organization", required=True)
    subject_class = db.StringField(required=True)
    subject_id = db.ObjectIdField(required=True)

    meta = {
        "indexes": [
            {"fields": ["user", "subject_class", "subject_id"], "unique": True},
            {"fields": ["subject_class", "subject_id"]},
            {"fields": ["user", "organization"]},
        ],
    }
```

#### Déclaration des policies sur les modèles

Chaque modèle déclare ses policies. Les rôles, le filtre public, tout est au même endroit.

```python
# udata/core/dataset/models.py
from udata.auth.policies import AccessPolicy

class Dataset(Owned, db.Document):
    read_policy = AccessPolicy(
        org_roles=("admin", "editor", "partial_editor"),
        public_filter=Q(private__ne=True, deleted=None, archived=None),
    )
    edit_policy = AccessPolicy(
        org_roles=("admin", "editor"),
    )

    @property
    def permissions(self):
        return {
            "edit": self.edit_policy.permission(self),
            "delete": self.edit_policy.permission(self),
        }
```

```python
# udata/core/reuse/models.py
class Reuse(Owned, db.Document):
    read_policy = AccessPolicy(
        org_roles=("admin", "editor", "partial_editor"),
        public_filter=Q(private__ne=True, datasets__0__exists=True, deleted=None),
    )
    edit_policy = AccessPolicy(
        org_roles=("admin", "editor"),
    )
```

```python
# udata/core/dataservices/models.py
class Dataservice(Owned, db.Document):
    read_policy = AccessPolicy(
        org_roles=("admin", "editor", "partial_editor"),
        public_filter=Q(private__ne=True, deleted_at=None, archived_at=None),
    )
    edit_policy = AccessPolicy(
        org_roles=("admin", "editor"),
    )
```

#### Usage unifié — ce qui remplace quoi

```python
# AVANT — la visibilité est définie à 3 endroits

# 1. Le queryset custom (par modèle)
class DatasetQuerySet(OwnedQuerySet):
    def visible(self):
        return self(private__ne=True, deleted=None, archived=None)

# 2. Le queryset Owned (générique)
class OwnedQuerySet:
    def visible_by_user(self, user, visible_query):
        ...

# 3. La permission per-object
class DatasetEditPermission(OwnablePermission):
    pass


# APRÈS — tout vient de la policy

# Listings publics (remplace visible())
Dataset.read_policy.queryset(Dataset.objects)

# Listings par user (remplace visible_by_user())
Dataset.read_policy.queryset(Dataset.objects, current_user)

# Listings éditables (nouveau)
Dataset.edit_policy.queryset(Dataset.objects, current_user)

# Per-object check (API views)
Dataset.edit_policy.permission(dataset).test()

# Sérialisation frontend
dataset.permissions["edit"].can()  # → True/False

# Elasticsearch
Dataset.read_policy.es_filter(current_user, Dataset)
```

#### Permissions composées hors `AccessPolicy`

Les cas spéciaux (discussions, harvest, transfer, notifications) qui ne suivent pas le pattern `Owned` restent des fonctions simples :

```python
# udata/core/discussions/permissions.py
from udata.auth.permissions import HasOrgRole, IsUser, Permission


def discussion_author_permission(discussion) -> Permission:
    if discussion.organization:
        return HasOrgRole(discussion.organization, "admin", "editor")
    return IsUser(discussion.user)


def discussion_close_permission(discussion) -> Permission:
    return discussion_author_permission(discussion) | discussion.subject.edit_policy.permission(discussion.subject)


def message_edit_permission(message) -> Permission:
    if message.posted_by_organization:
        return HasOrgRole(message.posted_by_organization, "admin", "editor")
    return IsUser(message.posted_by)
```

```python
# udata/core/organization/permissions.py
from udata.auth.permissions import HasOrgRole, Permission


def org_edit_permission(org) -> Permission:
    return HasOrgRole(org, "admin")


def org_private_permission(org) -> Permission:
    return HasOrgRole(org, "admin", "editor", "partial_editor")
```

```python
# udata/harvest/permissions.py
from udata.auth.permissions import HasOrgRole, IsUser, Deny, Permission


def harvest_source_permission(source) -> Permission:
    return source.edit_policy.permission(source)


def harvest_admin_permission(source) -> Permission:
    if source.organization:
        return HasOrgRole(source.organization, "admin")
    if source.owner:
        return IsUser(source.owner)
    return Deny()
```

```python
# udata/features/transfer/permissions.py
from udata.auth.permissions import Deny, HasOrgRole, IsUser, Permission


def transfer_permission(subject) -> Permission:
    if subject.organization:
        return HasOrgRole(subject.organization, "admin")
    if subject.owner:
        return IsUser(subject.owner)
    return Deny()


def transfer_response_permission(transfer) -> Permission:
    from udata.models import Organization

    if isinstance(transfer.recipient, Organization):
        return HasOrgRole(transfer.recipient, "admin")
    return IsUser(transfer.recipient)
```

```python
# udata/features/notifications/permissions.py
from udata.auth.permissions import IsUser, Permission


def notification_edit_permission(notification) -> Permission:
    return IsUser(notification.user)
```

#### Intégration avec `@api.secure`

Changement minimal dans `udata/api/__init__.py` :

```python
# Avant
from udata.auth import Permission, PermissionDenied, RoleNeed, current_user, login_user

class UDataApi(Api):
    def secure(self, func):
        if isinstance(func, str):
            return self._apply_permission(Permission(RoleNeed(func)))
        elif isinstance(func, Permission):
            return self._apply_permission(func)
        else:
            return self._apply_secure(func)

# Après
from udata.auth.permissions import HasRole, Permission, PermissionDenied
from udata.auth import current_user, login_user

class UDataApi(Api):
    def secure(self, func):
        if isinstance(func, str):
            return self._apply_permission(HasRole(func))
        elif isinstance(func, Permission):
            return self._apply_permission(func)
        else:
            return self._apply_secure(func)
```

`_apply_secure` utilise `permission.require()` qui fonctionne grâce à `_PermissionContext`.

#### Nouveau rôle `partial_editor`

```python
# udata/core/organization/constants.py
ORG_ROLES = {
    "admin": _("Administrator"),
    "editor": _("Editor"),
    "partial_editor": _("Partial editor"),
}
```

#### Suppression de `inject_organization_needs`

Le signal handler `inject_organization_needs` dans `udata/core/organization/permissions.py` est supprimé. Les permissions sont évaluées paresseusement via `HasOrgRole.check()` qui appelle `org.member(current_user)`.

Gain : plus de query MongoDB systématique à chaque requête authentifiée.

---

## 2. Ce qui change, ce qui ne change pas

### Change

| Composant | Avant | Après |
|-----------|-------|-------|
| Base permission | Flask-Principal `Permission` + needs/provides | `Permission` ABC avec `check()` |
| Bypass admin | `RoleNeed("admin")` injecté dans le constructeur | `can()` vérifie `sysadmin` directement |
| Org permissions | `OrganizationNeed` injecté à chaque requête | `HasOrgRole` vérifie lazily |
| Classes permission | 15+ classes, la plupart identiques | `AccessPolicy` sur le modèle + fonctions pour les cas spéciaux |
| Visibilité queryset | `visible()` par modèle + `visible_by_user()` générique | `policy.queryset(qs, user)` unifié |
| Discussion close | Hack `.union()` | `author_perm \| subject_perm` |
| Per-object | Impossible | `HasObjectPermission` + `ObjectPermission` |
| Elasticsearch | Filtres séparés dans les search adapters | `policy.es_filter(user, Model)` |

### Ne change pas

| Composant | Raison |
|-----------|--------|
| `fields.Permission` (API) | Appelle `.can()` → fonctionne |
| `@api.secure` / `@api.secure(perm)` | Utilise `.require()` → `_PermissionContext` assure la compatibilité |
| `model.permissions` property | Retourne toujours un dict de Permission → `.can()` |
| Flask-Security-Too | Reste installé, continue à gérer auth/login |
| Flask-Principal (package) | Reste installé (dépendance de Flask-Security-Too), mais plus importé par udata |

---

## 3. Migration

### Phase 1 : Ajouter le nouveau système à côté de l'ancien

1. Créer `udata/auth/permissions.py` (les primitives)
2. Créer `udata/auth/policies.py` (`AccessPolicy`)
3. Créer `udata/core/object_permissions/models.py` (le modèle)
4. Ajouter `partial_editor` à `ORG_ROLES`
5. Garder les anciens fichiers de permissions intacts

### Phase 2 : Migrer module par module

Pour chaque module (dataset, reuse, dataservices, organization, discussions, harvest, transfer, notifications, pages, topics) :

1. Ajouter `read_policy` / `edit_policy` sur le modèle
2. Réécrire `permissions.py` avec les nouvelles fonctions
3. Mettre à jour les imports dans `api.py` et `models.py`
4. Remplacer les appels à `visible()` / `visible_by_user()` par `policy.queryset()`
5. Vérifier que les tests passent

### Phase 3 : Nettoyage

1. Supprimer `inject_organization_needs` de `organization/permissions.py`
2. Supprimer les querysets custom (`DatasetQuerySet.visible()`, `ReuseQuerySet.visible()`, etc.)
3. Mettre à jour `api/__init__.py` pour importer depuis `udata.auth.permissions`
4. Supprimer les imports Flask-Principal de tout le codebase sauf `udata/auth/__init__.py` (qui peut rester comme re-export pour Flask-Security)
5. Supprimer `PostEditPermission`, `BadgePermission` et autres dead code

### Phase 4 : API pour gérer les `ObjectPermission`

Créer les endpoints pour que les org admins puissent assigner/retirer des permissions par objet aux partial editors.
