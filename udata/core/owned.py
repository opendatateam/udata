import logging

from blinker import signal
from mongoengine import NULLIFY, Q, post_save
from mongoengine.fields import ReferenceField

from udata.api_fields import field
from udata.core.organization.models import Organization
from udata.core.user.models import User
from udata.mongo.queryset import UDataQuerySet
from udata.core.user.api_fields import user_ref_fields
from udata.core.organization.api_fields import org_ref_fields
from udata.core.organization.permissions import OrganizationPrivatePermission
from udata.mongo.errors import FieldValidationError
from udata.i18n import lazy_gettext as _

log = logging.getLogger(__name__)


class OwnedQuerySet(UDataQuerySet):
    def owned_by(self, *owners):
        qs = Q()
        for owner in owners:
            qs |= Q(owner=owner) | Q(organization=owner)
        return self(qs)


class Owned(object):
    '''
    A mixin to factorize owning behvaior between users and organizations.
    '''
    owner = field(
        ReferenceField(User, reverse_delete_rule=NULLIFY),
        nested_fields=user_ref_fields,
        description="Only present if organization is not set. Can only be set to the current authenticated user.",
    )
    organization = field(
        ReferenceField(Organization, reverse_delete_rule=NULLIFY),
        nested_fields=org_ref_fields,
        description="Only present if owner is not set. Can only be set to an organization of the current authenticated user.",
    )

    on_owner_change = signal('Owned.on_owner_change')

    meta = {
        'indexes': [
            'owner',
            'organization',
        ],
        'queryset_class': OwnedQuerySet,
    }

    def clean(self):
        '''
        Verify owner consistency and fetch original owner before the new one erase it.
        '''
        from udata.auth import current_user, admin_permission

        changed_fields = self._get_changed_fields()
        if 'organization' in changed_fields and 'owner' in changed_fields:
            # Ownership changes (org to owner or the other way around) have already been made
            return
        if 'organization' in changed_fields:
            if current_user.is_authenticated and self.owner.organization and not OrganizationPrivatePermission(self.owner.organization).can():
                raise FieldValidationError(_("Permission denied for this organization"), field="organization")

            if self.owner:
                # Change from owner to organization
                self._previous_owner = self.owner
                self.owner = None
            else:
                # Change from org to another
                # Need to fetch previous value in base
                original = self.__class__.objects.only('organization').get(pk=self.pk)
                self._previous_owner = original.organization
        elif 'owner' in changed_fields:
            if current_user.is_authenticated and self.owner.user and not admin_permission and current_user.id != self.owner.user:
                raise FieldValidationError(_('You can only set yourself as owner'), field="owner")

            if self.organization:
                # Change from organization to owner
                self._previous_owner = self.organization
                self.organization = None
            else:
                # Change from owner to another
                # Need to fetch previous value in base
                original = self.__class__.objects.only('owner').get(pk=self.pk)
                self._previous_owner = original.owner


def owned_post_save(sender, document, **kwargs):
    '''
    Owned mongoengine.post_save signal handler
    Dispatch the `Owned.on_owner_change` signal
    once the document has been saved including the previous owner.

    The signal handler should have the following signature:
    ``def handler(document, previous)``
    '''
    if isinstance(document, Owned) and hasattr(document, '_previous_owner'):
        Owned.on_owner_change.send(document, previous=document._previous_owner)


post_save.connect(owned_post_save)
