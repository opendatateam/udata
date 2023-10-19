from udata.models import db


__all__ = ('ContactPoint', )


class ContactPoint(db.Document):
    email = db.StringField(max_length=255, required=True)
    name = db.StringField(max_length=255, required=True)
