from email_validator import EmailNotValidError, validate_email
from flask import current_app
from mongoengine.errors import ValidationError
from mongoengine.fields import StringField
from urlextract import URLExtract

from udata.api_fields import field, generate_fields
from udata.core.owned import Owned, OwnedQuerySet
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

_url_extractor = URLExtract()

MASK_FIELDS = ("id", "name", "email", "contact_form", "role")


def check_no_urls(value, field, **_kwargs):
    if value and _url_extractor.find_urls(value):
        raise FieldValidationError(_("URLs not allowed in this field"), field=field)


def check_is_email(value, field, **_kwargs):
    if value:
        try:
            kwargs = current_app.config.get("SECURITY_EMAIL_VALIDATOR_ARGS", {}) or {}
            validate_email(value, **kwargs)
        except EmailNotValidError:
            raise FieldValidationError(_("Invalid email address"), field=field)


@generate_fields(mask=",".join(MASK_FIELDS))
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
