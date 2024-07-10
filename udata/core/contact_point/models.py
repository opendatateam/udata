from udata.core.owned import Owned, OwnedQuerySet
from udata.mongo import db

__all__ = ("ContactPoint",)


class ContactPoint(db.Document, Owned):
    email = db.StringField(max_length=255, required=True)
    name = db.StringField(max_length=255, required=True)

    meta = {"queryset_class": OwnedQuerySet}
