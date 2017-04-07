# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import datetime

from udata.models import db

log = logging.getLogger(__name__)

__all__ = ('Issue',)


class Message(db.EmbeddedDocument):
    content = db.StringField(required=True)
    posted_on = db.DateTimeField(default=datetime.now, required=True)
    posted_by = db.ReferenceField('User')


class Issue(db.Document):
    user = db.ReferenceField('User')
    subject = db.GenericReferenceField()
    title = db.StringField(required=True)
    discussion = db.ListField(db.EmbeddedDocumentField(Message))
    created = db.DateTimeField(default=datetime.now, required=True)
    closed = db.DateTimeField()
    closed_by = db.ReferenceField('User')

    meta = {
        'indexes': [
            'user',
            'subject',
            '-created'
        ],
        'ordering': ['-created'],
    }
