import re

from urlextract import URLExtract

from udata.api_fields import field, generate_fields
from udata.core.owned import Owned, OwnedQuerySet
from udata.i18n import lazy_gettext as _
from udata.mongo import db
from udata.mongo.errors import FieldValidationError

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

_url_extractor = URLExtract()

# Simple email regex matching WTForms' Email validator behavior
_email_re = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

MASK_FIELDS = ("id", "name", "email", "contact_form", "role")


def check_no_urls(value, field, **_kwargs):
    if value and _url_extractor.find_urls(value):
        raise FieldValidationError(_("URLs not allowed in this field"), field=field)


def check_is_email(value, field, **_kwargs):
    if value and not _email_re.match(value):
        raise FieldValidationError(_("Invalid email address"), field=field)


@generate_fields(mask=",".join(MASK_FIELDS))
class ContactPoint(db.Document, Owned):
    name = field(db.StringField(max_length=255, required=True), checks=[check_no_urls])
    email = field(db.StringField(max_length=255), checks=[check_is_email])
    contact_form = field(db.URLField())
    role = field(db.StringField(required=True, choices=list(CONTACT_ROLES)))

    meta = {"queryset_class": OwnedQuerySet}

    def validate(self, clean=True):
        if self.role == "contact" and not self.email and not self.contact_form:
            raise db.ValidationError(
                _("At least an email or a contact form is required for a contact point")
            )
        return super().validate(clean=clean)
