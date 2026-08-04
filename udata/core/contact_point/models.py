from mongoengine.errors import ValidationError
from mongoengine.fields import StringField

from udata.api_fields import field, generate_fields
from udata.core.checks import check_is_email, check_no_urls
from udata.core.owned import Owned, OwnedQuerySet
from udata.i18n import lazy_gettext as _
from udata.mongo.document import UDataDocument as Document
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
