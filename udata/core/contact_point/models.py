from udata.core.owned import Owned, OwnedQuerySet
from udata.i18n import lazy_gettext as _
from udata.mongo import db

__all__ = ("ContactPoint",)


class ContactPoint(db.Document, Owned):
    name = db.StringField(max_length=255, required=True)
    email = db.StringField(max_length=255)
    contact_form = db.URLField()

    meta = {"queryset_class": OwnedQuerySet}

    def validate(self, clean=True):
        if not self.email and not self.contact_form:
            raise db.ValidationError(
                _("At least an email or a contact form is required for a contact point")
            )
        return super().validate(clean=clean)
