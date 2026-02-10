# Système de permissions udata

## 1. Audit du système actuel

### Architecture

Le système repose sur **Flask-Principal 0.4.0** (release 2013, ~486 lignes) utilisé indirectement via **Flask-Security-Too 5.7.1**.

```
Requête authentifiée
  → Flask-Security charge l'identité
  → Signal identity_loaded → inject_organization_needs()
      → Query MongoDB: toutes les orgs du user
      → Pour chaque org: ajoute OrganizationNeed(role, org_id) à l'identité
  → La requête accède à l'endpoint
  → @api.secure vérifie l'authentification
  → permission.test() compare les needs de la permission avec les provides de l'identité
```

**Modèle mental Flask-Principal :** les permissions sont des ensembles de "needs". L'identité de l'utilisateur fournit des "provides". Si l'intersection est non-vide, l'accès est accordé. C'est un modèle push : toutes les permissions sont pré-calculées au chargement de l'identité.

### Rôles

**Système** (champ `roles` du User) :

| Rôle | Effet réel |
|------|-----------|
| `admin` | Bypass universel de toutes les permissions |
| `editor` | **Aucun** — jamais vérifié dans le code |
| `moderator` | **Aucun** — jamais vérifié dans le code |

**Organisation** (embedded dans `Member`) :

| Rôle | Droits |
|------|--------|
| `admin` | Gère l'org (membres, settings) + édite tout le contenu de l'org |
| `editor` | Édite tout le contenu de l'org, ne gère pas l'org elle-même |

### Classe `Permission` (udata)

```python
# udata/auth/__init__.py
class Permission(BasePermission):
    def __init__(self, *needs):
        # Ajoute automatiquement le bypass admin à TOUTES les permissions
        super().__init__(RoleNeed("admin"), *needs)
```

Toutes les permissions héritant de cette classe accordent automatiquement l'accès aux sysadmins. C'est le mécanisme central du bypass admin.

### Matrice d'accès actuelle

| Entité | Qui peut créer | Qui peut éditer | Qui peut supprimer |
|--------|---------------|-----------------|-------------------|
| Dataset | tout authentifié | owner / org admin / org editor | idem |
| Reuse | tout authentifié | owner / org admin / org editor | idem |
| Dataservice | tout authentifié | owner / org admin / org editor | idem |
| Organization | tout authentifié | org admin | org admin |
| Discussion | tout authentifié | auteur / org auteur | auteur / org auteur |
| Fermer discussion | — | auteur discussion OU owner du sujet | — |
| Harvest source | tout authentifié | org admin / owner (pas editor) | idem |
| Page | tout authentifié | owner / org admin / org editor | idem |
| Post | admin système | admin système | admin système |
| Badge (CRUD) | admin système | admin système | admin système |
| Featured | admin système | admin système | admin système |
| User (admin CRUD) | admin système | admin système | admin système |

### Problèmes identifiés

**Architecture :**

1. **Granularité trop grossière.** La permission est binaire par organisation : soit on peut tout éditer, soit rien. Pas de permission par objet.

2. **Pre-loading systématique.** `inject_organization_needs` query toutes les orgs du user à chaque requête authentifiée, même si la requête ne vérifie aucune permission (GET public, etc.). Pas de `.only()` → documents complets chargés.

3. **Rôles système `editor`/`moderator` inutilisés.** Définis dans `ROLES` mais jamais vérifiés par aucune permission. Dead config.

4. **`PostEditPermission` est du dead code.** `Permission()` sans needs = admin only. Tous les endpoints post utilisent déjà `@api.secure(admin_permission)`. La classe n'est jamais appelée.

**Code :**

5. **Booléen implicite sur `admin_permission`.** Dans `owned.py`, `if admin_permission:` fonctionne car Flask-Principal définit `__bool__` → `.can()`. Mais c'est un piège de lisibilité.

6. **Duplication.** `ReuseEditPermission` réimplémente `OwnablePermission` au lieu d'en hériter. 15+ classes de permission pour ~3 logiques distinctes.

7. **`TransferPermission` : variable potentiellement non définie.** Si `subject.organization` et `subject.owner` sont tous deux `None`, `need` est undefined → `NameError`.

8. **`BadgePermission` cassé pour les user-owned objects.** Utilise `subject.id` comme `organization_id` quand il n'y a pas d'org → aucun user ne matche. Mais dead code car les endpoints utilisent `admin_permission` directement.

9. **Discussion close : hack `.union()`.** Fonction qui simule une classe car l'héritage multiple ne fonctionne pas avec les permissions Flask-Principal. Fragile.

**Flask-Principal lui-même :**

10. **Dernière release : 2013.** Maintenu sous perfusion par le fork pallets-eco, uniquement parce que Flask-Security-Too en dépend. 486 lignes. Pas d'évolution prévue.

11. **Modèle inadapté aux permissions par objet.** Le système needs/provides est conçu pour des rôles globaux ou par organisation, pas pour des ACL par objet. Ajouter des permissions granulaires demanderait soit d'injecter des centaines de needs par requête, soit de contourner Flask-Principal.

---

## 2. Nouveau système proposé

### Principes

1. **Les permissions sont des prédicats composables.** Une permission = une question "le user courant peut-il faire X ?", évaluée paresseusement.
2. **Composition avec `|` et `&`.** Pas de listes de needs, pas d'intersection d'ensembles. Juste de la logique booléenne.
3. **Évaluation lazy.** Pas de pre-loading. L'appartenance à une org est vérifiée au moment du check, pas au chargement de l'identité.
4. **Admin bypass intégré dans `can()`.** Chaque permission accorde automatiquement l'accès aux sysadmins.
5. **Aucune dépendance à Flask-Principal.** Flask-Principal reste installé (Flask-Security-Too en a besoin) mais on n'utilise plus ses classes Permission/Need.
6. **Même interface publique.** `permission.can()`, `.test()`, `bool(permission)` fonctionnent comme avant. La sérialisation API (`fields.Permission` appelle `.can()`) ne change pas.

### Implémentation

#### `udata/auth/permissions.py` — Les primitives

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from flask_security import current_user


class PermissionDenied(Exception):
    pass


class Permission(ABC):
    """A composable authorization predicate."""

    @abstractmethod
    def check(self) -> bool:
        """Raw permission logic. Override this.

        Does not include admin bypass — that's handled by can().
        Used internally by AnyOf/AllOf for composition.
        """
        ...

    def can(self) -> bool:
        if current_user.is_authenticated and current_user.sysadmin:
            return True
        return self.check()

    def test(self):
        if not self.can():
            raise PermissionDenied("You do not have the permission to modify that object.")

    # Flask-Principal compatibility: permission.require() is used by api.secure
    def require(self):
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
    """Minimal context manager for api.secure compatibility.

    Replaces Flask-Principal's IdentityContext. api.secure does:
        with permission.require():
            return func(...)
    """

    def __init__(self, permission: Permission):
        self._permission = permission

    def __enter__(self):
        if not self._permission.can():
            raise PermissionDenied(
                "You do not have the permission to modify that object."
            )
        return self

    def __exit__(self, *args):
        pass

    def can(self):
        return self._permission.can()


# --- Leaf predicates ---


class Allow(Permission):
    """Always granted, even for anonymous users."""

    def check(self) -> bool:
        return True


class Deny(Permission):
    """Only admins pass (via the bypass in can())."""

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
    """Granted if the current user is a member of the org with one of the given roles."""

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
    """Granted if the current user has an explicit per-object permission.

    This is the building block for partial editors: users who can only
    edit a specific list of objects within an organization.
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
    """Granted if ANY sub-permission passes."""

    def __init__(self, *permissions: Permission):
        self._permissions = permissions

    def check(self) -> bool:
        return any(p.check() for p in self._permissions)

    def __repr__(self) -> str:
        return f"<AnyOf {' | '.join(repr(p) for p in self._permissions)}>"


class AllOf(Permission):
    """Granted if ALL sub-permissions pass."""

    def __init__(self, *permissions: Permission):
        self._permissions = permissions

    def check(self) -> bool:
        return all(p.check() for p in self._permissions)

    def __repr__(self) -> str:
        return f"<AllOf {' & '.join(repr(p) for p in self._permissions)}>"


# --- Convenience ---

admin_permission = HasRole("admin")
```

#### `udata/core/object_permissions/models.py` — Le modèle pour les permissions par objet

```python
from bson import ObjectId
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

#### Permissions composées par domaine

Chaque module remplace sa classe de permission par une fonction retournant un `Permission`. L'interface pour les modèles (`.permissions` property) ne change pas.

```python
# udata/core/dataset/permissions.py

from udata.auth.permissions import (
    Allow,
    Deny,
    HasObjectPermission,
    HasOrgRole,
    IsUser,
    Permission,
)


def ownable_permission(obj) -> Permission:
    """Permission to edit an owned object (dataset, reuse, dataservice, page, topic, etc.)."""
    if obj.organization:
        return (
            HasOrgRole(obj.organization, "admin", "editor")
            | HasObjectPermission(obj)
        )
    if obj.owner:
        return IsUser(obj.owner)
    return Deny()


def ownable_read_permission(obj) -> Permission:
    """Permission to read a potentially private object.

    Public objects are visible by everyone. Private objects require
    ownership, org membership, or explicit assignment.
    """
    if not getattr(obj, "private", False):
        return Allow()
    if obj.organization:
        return (
            HasOrgRole(obj.organization, "admin", "editor", "partial_editor")
            | HasObjectPermission(obj)
        )
    if obj.owner:
        return IsUser(obj.owner)
    return Deny()


# Aliases for clarity in models — same logic, distinct names for distinct intent.
def dataset_edit_permission(dataset) -> Permission:
    return ownable_permission(dataset)


def resource_edit_permission(dataset) -> Permission:
    return ownable_permission(dataset)
```

```python
# udata/core/reuse/permissions.py

from udata.core.dataset.permissions import ownable_permission, Permission


def reuse_edit_permission(reuse) -> Permission:
    return ownable_permission(reuse)
```

```python
# udata/core/dataservices/permissions.py

from udata.core.dataset.permissions import ownable_permission, Permission


def dataservice_edit_permission(dataservice) -> Permission:
    return ownable_permission(dataservice)
```

```python
# udata/core/organization/permissions.py

from udata.auth.permissions import HasOrgRole, Permission


def org_edit_permission(org) -> Permission:
    """Only org admins can manage the organization itself."""
    return HasOrgRole(org, "admin")


def org_private_permission(org) -> Permission:
    """Any org member can see private org assets."""
    return HasOrgRole(org, "admin", "editor", "partial_editor")
```

```python
# udata/core/discussions/permissions.py

from udata.auth.permissions import HasOrgRole, IsUser, Permission
from udata.core.dataset.permissions import ownable_permission


def discussion_author_permission(discussion) -> Permission:
    if discussion.organization:
        return HasOrgRole(discussion.organization, "admin", "editor")
    return IsUser(discussion.user)


def discussion_close_permission(discussion) -> Permission:
    return discussion_author_permission(discussion) | ownable_permission(discussion.subject)


def message_edit_permission(message) -> Permission:
    if message.posted_by_organization:
        return HasOrgRole(message.posted_by_organization, "admin", "editor")
    return IsUser(message.posted_by)
```

```python
# udata/harvest/permissions.py

from udata.auth.permissions import HasOrgRole, IsUser, Permission
from udata.core.dataset.permissions import ownable_permission


def harvest_source_permission(source) -> Permission:
    """Basic ops (preview). Editors included."""
    return ownable_permission(source)


def harvest_admin_permission(source) -> Permission:
    """Sensitive ops (edit, delete, run). Editors excluded."""
    if source.organization:
        return HasOrgRole(source.organization, "admin")
    if source.owner:
        return IsUser(source.owner)
    from udata.auth.permissions import Deny
    return Deny()
```

```python
# udata/features/transfer/permissions.py

from udata.auth.permissions import Deny, HasOrgRole, IsUser, Permission


def transfer_permission(subject) -> Permission:
    """Who can initiate a transfer (org admins and direct owners only)."""
    if subject.organization:
        return HasOrgRole(subject.organization, "admin")
    if subject.owner:
        return IsUser(subject.owner)
    return Deny()


def transfer_response_permission(transfer) -> Permission:
    """Who can accept/refuse a transfer."""
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

#### Utilisation dans les modèles

L'interface ne change pas. Seul l'import change.

```python
# Avant (dataset/models.py)
@property
def permissions(self):
    from .permissions import DatasetEditPermission, ResourceEditPermission
    return {
        "delete": DatasetEditPermission(self),
        "edit": DatasetEditPermission(self),
        "edit_resources": ResourceEditPermission(self),
    }

# Après
@property
def permissions(self):
    from .permissions import dataset_edit_permission, resource_edit_permission
    return {
        "delete": dataset_edit_permission(self),
        "edit": dataset_edit_permission(self),
        "edit_resources": resource_edit_permission(self),
    }
```

La sérialisation API ne change pas : `fields.Permission` appelle `.can()` sur l'objet retourné.

```python
# udata/api/fields.py — AUCUN CHANGEMENT
class Permission(Boolean):
    def format(self, field):
        return field.can()
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

#### Intégration avec les querysets

```python
# udata/core/owned.py
class OwnedQuerySet(UDataQuerySet):
    def visible_by_user(self, user: User, visible_query: Q):
        if user.is_anonymous:
            return self(visible_query)
        if user.sysadmin:
            return self()

        owners: list[User | Organization] = list(user.organizations) + [user.id]
        owned_qs = self.__class__(self._document, self._collection_obj).owned_by(*owners)

        # Objects explicitly assigned to this user (partial editors)
        from udata.core.object_permissions.models import ObjectPermission

        assigned_ids = ObjectPermission.objects(
            user=user.id,
            subject_class=self._document.__name__,
        ).distinct("subject_id")

        return self(visible_query | owned_qs._query_obj | Q(id__in=assigned_ids))
```

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

## 3. Ce qui change, ce qui ne change pas

### Change

| Composant | Avant | Après |
|-----------|-------|-------|
| Base permission | Flask-Principal `Permission` + needs/provides | `Permission` ABC avec `check()` |
| Bypass admin | `RoleNeed("admin")` injecté dans le constructeur | `can()` vérifie `sysadmin` directement |
| Org permissions | `OrganizationNeed` injecté à chaque requête | `HasOrgRole` vérifie lazily |
| Classes permission | 15+ classes, la plupart identiques | ~10 fonctions d'une ligne |
| Discussion close | Hack `.union()` | `author_perm \| subject_perm` |
| Per-object | Impossible | `HasObjectPermission` + `ObjectPermission` |

### Ne change pas

| Composant | Raison |
|-----------|--------|
| `fields.Permission` (API) | Appelle `.can()` → fonctionne |
| `@api.secure` / `@api.secure(perm)` | Utilise `.require()` → `_PermissionContext` assure la compatibilité |
| `model.permissions` property | Retourne toujours un dict de Permission → `.can()` |
| `OwnedQuerySet.visible_by_user()` | Même logique + ajout des assigned_ids |
| Flask-Security-Too | Reste installé, continue à gérer auth/login |
| Flask-Principal (package) | Reste installé (dépendance de Flask-Security-Too), mais plus importé par udata |

---

## 4. Migration

### Phase 1 : Ajouter le nouveau système à côté de l'ancien

1. Créer `udata/auth/permissions.py` (les primitives)
2. Créer `udata/core/object_permissions/models.py` (le modèle)
3. Ajouter `partial_editor` à `ORG_ROLES`
4. Garder les anciens fichiers de permissions intacts

### Phase 2 : Migrer module par module

Pour chaque module (dataset, reuse, dataservices, organization, discussions, harvest, transfer, notifications, pages, topics) :

1. Réécrire `permissions.py` avec les nouvelles fonctions
2. Mettre à jour les imports dans `api.py` et `models.py`
3. Vérifier que les tests passent

### Phase 3 : Nettoyage

1. Supprimer `inject_organization_needs` de `organization/permissions.py`
2. Mettre à jour `api/__init__.py` pour importer depuis `udata.auth.permissions`
3. Mettre à jour `owned.py` : remplacer `OrganizationPrivatePermission` par `org_private_permission`, ajouter le query `ObjectPermission` dans `visible_by_user`
4. Supprimer les imports Flask-Principal de tout le codebase sauf `udata/auth/__init__.py` (qui peut rester comme re-export pour Flask-Security)
5. Supprimer `PostEditPermission`, `BadgePermission` et autres dead code

### Phase 4 : API pour gérer les `ObjectPermission`

Créer les endpoints pour que les org admins puissent assigner/retirer des permissions par objet aux partial editors.
