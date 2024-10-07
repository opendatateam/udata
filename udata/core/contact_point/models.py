from udata.core.owned import Owned, OwnedQuerySet
from udata.mongo import db

__all__ = ("ContactPoint",)


class ContactPoint(db.Document, Owned):
    name = db.StringField(max_length=255, required=True)
    email = db.StringField(max_length=255)
    contact_form = db.URLField()

    meta = {"queryset_class": OwnedQuerySet}
