import logging
from datetime import datetime

from blinker import Signal
from mongoengine.signals import post_save

from udata.i18n import lazy_gettext as _
from udata.mongo import db

log = logging.getLogger(__name__)

__all__ = ("Transfer",)


TRANSFER_STATUS = {
    "pending": _("Pending"),
    "accepted": _("Accepted"),
    "refused": _("Refused"),
}


class Transfer(db.Document):
    user = db.ReferenceField("User")
    owner = db.GenericReferenceField(required=True)
    recipient = db.GenericReferenceField(required=True)
    subject = db.GenericReferenceField(required=True)
    comment = db.StringField()
    status = db.StringField(choices=list(TRANSFER_STATUS), default="pending")

    created = db.DateTimeField(default=datetime.utcnow, required=True)

    responded = db.DateTimeField()
    responder = db.ReferenceField("User")
    response_comment = db.StringField()

    on_create = Signal()

    meta = {
        "indexes": [
            "owner",
            "recipient",
            "created",
            "status",
        ]
    }

    @classmethod
    def post_save(cls, sender, document, **kwargs):
        """Handle post save signal for Transfer documents."""
        # Only trigger on_create signal on creation, not on every save
        if kwargs.get("created"):
            cls.on_create.send(document)


# Connect the post_save signal
post_save.connect(Transfer.post_save, sender=Transfer)
