from mongoengine.errors import ValidationError
from mongoengine.fields import StringField

from udata.api_fields import field, generate_fields
from udata.core.checks import check_is_email, check_no_urls
from udata.core.organization.models import Organization
from udata.core.owned import Owned, OwnedQuerySet, ownership_filter
from udata.core.user.models import User
from udata.i18n import lazy_gettext as _
from udata.mongo.document import UDataDocument as Document
from udata.mongo.errors import FieldValidationError
from udata.mongo.url_field import URLField

__all__ = ("ContactPoint",)


CONTACT_ROLES = {
    "contact": _("Contact"),
    "creator": _("Creator"),
    "publisher": _("Publisher"),
    "rightsHolder": _("Rights Holder"),
    "custodian": _("Custodian"),
    "distributor": _("Distributor"),
    "originator": _("Originator"),
    "principalInvestigator": _("Principal Investigator"),
    "processor": _("Processor"),
    "resourceProvider": _("Resource Provider"),
    "user": _("User"),
}

MASK_FIELDS = ("id", "name", "email", "contact_form", "role")


@generate_fields(page_mask=",".join(MASK_FIELDS))
class ContactPoint(Document, Owned):
    name = field(StringField(max_length=255, required=True), checks=[check_no_urls])
    email = field(StringField(max_length=255), checks=[check_is_email])
    contact_form = field(URLField())
    role = field(StringField(required=True, choices=list(CONTACT_ROLES)))

    meta = {"queryset_class": OwnedQuerySet}

    def validate(self, clean=True):
        if self.role == "contact" and not self.email and not self.contact_form:
            raise ValidationError(
                _("At least an email or a contact form is required for a contact point")
            )
        return super().validate(clean=clean)

    def for_owner(self, owner: Organization | User) -> "ContactPoint":
        """The same contact point, owned by `owner`, created if it does not exist yet.

        Contact points are never moved from one owner to another: a single one is shared
        by all the objects of its owner, so moving it would silently change the contact
        of the objects that stayed behind.
        """
        contact_point, _created = ContactPoint.objects.get_or_create(
            name=self.name,
            email=self.email,
            contact_form=self.contact_form,
            role=self.role,
            **ownership_filter(owner),
        )
        return contact_point


def validate_contact_points_ownership(document) -> None:
    """Check that the contact points of `document` belong to whoever owns it.

    Enforced on the model rather than on the API layer because ownership also changes
    through transfers and harvesting, and neither goes through a form or through `patch()`.
    Call it from `validate()` and after `Owned.clean` has run: errors raised from `clean()`
    are re-wrapped by mongoengine under `__all__`, losing the field this one is about, and
    ownership is ambiguous until `Owned.clean` clears the field the object is moving away
    from.
    """
    for contact_point in document.contact_points:
        if (
            contact_point.organization != document.organization
            or contact_point.owner != document.owner
        ):
            raise FieldValidationError(
                _("Contact point {id} does not belong to the owner of this object").format(
                    id=contact_point.id
                ),
                field="contact_points",
            )
