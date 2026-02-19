import logging
from datetime import datetime

from blinker import Signal
from mongoengine.fields import DateTimeField, GenericReferenceField, ReferenceField, StringField
from mongoengine.signals import post_save

from udata.i18n import lazy_gettext as _
from udata.mongo.document import UDataDocument as Document

log = logging.getLogger(__name__)

__all__ = ("Transfer",)


TRANSFER_STATUS = {
    "pending": _("Pending"),
    "accepted": _("Accepted"),
    "refused": _("Refused"),
}


class Transfer(Document):
    user = ReferenceField("User")
    owner = GenericReferenceField(required=True)
    recipient = GenericReferenceField(required=True)
    subject = GenericReferenceField(required=True)
    comment = StringField()
    status = StringField(choices=list(TRANSFER_STATUS), default="pending")

    created = DateTimeField(default=datetime.utcnow, required=True)

    responded = DateTimeField()
    responder = ReferenceField("User")
    response_comment = StringField()

    on_create = Signal()
    after_handle = Signal()
    after_delete = Signal()

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

    def delete(self, *args, **kwargs):
        """Delete the transfer and ensure after_delete signal is triggered"""
        result = super().delete(*args, **kwargs)
        self.after_delete.send(self)
        return result


# Connect the post_save signal
post_save.connect(Transfer.post_save, sender=Transfer)
