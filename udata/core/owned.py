import logging

from blinker import signal
from mongoengine import NULLIFY, Q, post_save
from mongoengine.fields import ReferenceField

from udata.api_fields import field
from udata.core.checks import only_creation
from udata.core.organization.models import Organization
from udata.core.user.models import User
from udata.i18n import lazy_gettext as _
from udata.mongo.errors import FieldValidationError
from udata.mongo.queryset import UDataQuerySet

log = logging.getLogger(__name__)


class OwnedQuerySet(UDataQuerySet):
    def owned_by(self, *owners):
        qs = Q()
        for owner in owners:
            qs |= Q(owner=owner) | Q(organization=owner)
        return self(qs)

    def visible_by_user(self, user: User, visible_query: Q):
        """Return EVERYTHING visible to the user."""
        if user.is_anonymous:
            return self(visible_query)

        if user.sysadmin:
            return self()

        owners = list(user.organizations) + [user.id]
        # We create a new queryset because we want a pristine self._query_obj.
        owned_qs: OwnedQuerySet = self.__class__(self._document, self._collection_obj).owned_by(
            *owners
        )

        return self(visible_query | owned_qs._query_obj)


def ownership_filter(owner: Organization | User) -> dict:
    """The ownership fields of `owner`, whichever kind of owner it is.

    Both fields are always set: an owner owns through one of them and, just as importantly,
    not through the other. A filter naming only one would also match documents whose other
    field points at somebody else — an inconsistent state nothing forbids, since `Owned.clean`
    only clears a field an object is moving away from.
    """
    is_organization = isinstance(owner, Organization)
    return {
        "organization": owner if is_organization else None,
        "owner": None if is_organization else owner,
    }


def check_owner_is_current_user(owner, **_kwargs):
    from udata.auth import admin_permission, current_user

    if (
        current_user.is_authenticated
        and owner
        and not admin_permission
        and current_user.id != owner.id
    ):
        raise FieldValidationError(_("You can only set yourself as owner"), field="owner")


def check_organization_is_valid_for_current_user(organization, **_kwargs):
    from udata.auth import current_user
    from udata.models import Organization

    # An explicit null clears the producer, like `check_owner_is_current_user` above:
    # there is no organization to look up, let alone to check permissions on.
    if not organization:
        return

    org = Organization.objects(id=organization.id).first()
    if org is None:
        raise FieldValidationError(_("Unknown organization"), field="organization")

    if current_user.is_authenticated and not org.permissions["private"].can():
        raise FieldValidationError(
            _("Permission denied for this organization"), field="organization"
        )


class Owned(object):
    """
    A mixin to factorize owning behavior between users and organizations.
    """

    owner = field(
        ReferenceField(User, reverse_delete_rule=NULLIFY),
        description="Only present if organization is not set. Can only be set to the current authenticated user.",
        checks=[check_owner_is_current_user, only_creation],
        allow_null=True,
        filterable={},
    )
    organization = field(
        ReferenceField(Organization, reverse_delete_rule=NULLIFY),
        description="Only present if owner is not set. Can only be set to an organization of the current authenticated user.",
        checks=[check_organization_is_valid_for_current_user, only_creation],
        allow_null=True,
        filterable={},
    )

    on_owner_change = signal("Owned.on_owner_change")

    meta = {
        "indexes": [
            "owner",
            "organization",
        ],
        "queryset_class": OwnedQuerySet,
    }

    def clean(self):
        """
        Verify owner consistency and fetch original owner before the new one erase it.
        """

        changed_fields = self._get_changed_fields()
        if "organization" not in changed_fields and "owner" not in changed_fields:
            return
        # Setting one field moves the object away from the other one. Forms set both at once.
        if "owner" not in changed_fields:
            self.owner = None
        elif "organization" not in changed_fields:
            self.organization = None
        original = self.__class__.objects.only("owner", "organization").get(pk=self.pk)
        previous = original.organization or original.owner
        # A save nested in a `post_save` receiver sees the same changed fields with the new
        # owner already in base: it must keep the previous owner found by the outer save.
        if previous != (self.organization or self.owner):
            self._previous_owner = previous


def owned_post_save(sender, document, **kwargs):
    """
    Owned mongoengine.post_save signal handler
    Dispatch the `Owned.on_owner_change` signal
    once the document has been saved including the previous owner.

    The signal handler should have the following signature:
    ``def handler(document, previous)``
    """
    if isinstance(document, Owned) and hasattr(document, "_previous_owner"):
        # Consumed before sending: the instance outlives this save, and a later save of it
        # (or one nested in a receiver) would otherwise report the same change again.
        previous = document._previous_owner
        del document._previous_owner
        Owned.on_owner_change.send(document, previous=previous)


post_save.connect(owned_post_save)
