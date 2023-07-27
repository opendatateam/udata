import logging

from datetime import datetime

from udata.i18n import lazy_gettext as _
from udata.models import db

log = logging.getLogger(__name__)

__all__ = ('Transfer',)


TRANSFER_STATUS = {
    'pending': _('Pending'),
    'accepted': _('Accepted'),
    'refused': _('Refused'),
}


class Transfer(db.Document):
    owner = db.GenericReferenceField(required=True)
    recipient = db.GenericReferenceField(required=True)
    subject = db.GenericReferenceField(required=True)
    comment = db.StringField()
    status = db.StringField(choices=list(TRANSFER_STATUS), default='pending')

    created = db.DateTimeField(default=datetime.utcnow, required=True)

    responded = db.DateTimeField()
    responder = db.ReferenceField('User')
    response_comment = db.StringField()

    meta = {
        'indexes': [
            'owner',
            'recipient',
            'created',
            'status',
        ]
    }
